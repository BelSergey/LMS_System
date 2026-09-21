# LMS System — бэкенд платформы онлайн-обучения

Бэкенд-часть платформы для онлайн-курсов: пользователи создают курсы и уроки,
подписываются на обновления интересующих курсов и оплачивают материалы
через Stripe. При обновлении курса или урока подписчики получают email-
уведомление, а неактивные более 30 дней пользователи автоматически
блокируются по расписанию.

Стек: Django 5.2, Django REST Framework, Simple JWT, Celery + Celery Beat,
Redis, PostgreSQL, Nginx, Gunicorn, Stripe API, drf-spectacular
(Swagger/Redoc), Docker / Docker Compose, GitHub Actions (CI/CD).

## Возможности

- Регистрация и авторизация по email/паролю (JWT + классический сессионный
  вход для веб-интерфейса).
- Подтверждение email по ссылке при регистрации.
- CRUD над курсами и уроками с пагинацией (5 курсов / 10 уроков на страницу).
- Роли: обычный пользователь, модератор (группа `moderators`, может
  редактировать любые курсы и уроки, но не создавать и не удалять их),
  владелец объекта.
- Подписка/отписка от обновлений курса (toggle-эндпоинт).
- Уведомление подписчиков по email при обновлении курса или его уроков
  (не чаще раза в 4 часа на курс) — асинхронно через Celery.
- Оплата курсов и уроков через Stripe (создание продукта, цены, checkout-
  сессии) и проверка статуса оплаты.
- Автоматическая блокировка пользователей, не заходивших в систему 30+ дней
  (ежедневная задача Celery Beat).
- Автоматическая документация API (Swagger / Redoc).
- Полностью запускается одной командой через Docker Compose.

## Требования

- Docker и Docker Compose
- (для запуска без Docker: Python 3.12+, PostgreSQL 16, Redis 7)

## Установка и запуск

1. Клонируйте репозиторий и перейдите в него:

   ```bash
   git clone <url-репозитория>
   cd LMS_System
   ```

2. Создайте файл `.env` в корне проекта на основе `.env.example` и
   заполните своими значениями:

   ```env
   SECRET_KEY=django-insecure-change-me

   DB_NAME=lms_system
   DB_USER=lms_user
   DB_PASSWORD=lms_password
   DB_HOST=db
   DB_PORT=5432

   REDIS_HOST=redis
   REDIS_PORT=6379
   REDIS_DB=0

   DEFAULT_FROM_EMAIL=noreply@lms.com
   STRIPE_SECRET_KEY=sk_test_ваш_ключ
   ```

   > Значения `DB_HOST=db` и `REDIS_HOST=redis` — имена сервисов внутри
   > Docker-сети, менять их не нужно при запуске через Compose.

3. Соберите образы и запустите все сервисы одной командой:

   ```bash
   docker compose up --build -d
   ```

   Будут подняты 6 контейнеров:

   | Сервис | Назначение |
   |---|---|
   | `db` | PostgreSQL, хранит данные приложения |
   | `redis` | брокер сообщений и result-backend для Celery |
   | `web` | Django-приложение (миграции + collectstatic + gunicorn), не имеет внешнего доступа |
   | `celery` | воркер, выполняющий фоновые задачи |
   | `celery-beat` | планировщик периодических задач |
   | `nginx` | reverse-proxy и раздача статики/медиа, единственный сервис с внешним доступом |

4. Создайте суперпользователя и группу модераторов:

   ```bash
   docker compose exec web python manage.py createsuperuser
   docker compose exec web python manage.py create_groups
   ```

5. После запуска приложение доступно на [http://localhost/](http://localhost/)
   (порт 80, через Nginx) при локальном запуске, либо на `http://<IP-сервера>/`
   при развёртывании на удалённом сервере (см. раздел «Развёртывание» ниже).

### Полезные команды

Логи конкретного сервиса:
```bash
docker compose logs -f web
```

Остановить все сервисы:
```bash
docker compose down
```

Остановить и удалить volumes (полный сброс данных БД):
```bash
docker compose down -v
```

### Периодические задачи

Расписание задаётся в `CELERY_BEAT_SCHEDULE` (`config/settings.py`):
задача `users.tasks.block_inactive_users` запускается ежедневно в полночь
и деактивирует пользователей, не заходивших в систему более 30 дней.
Уведомления подписчикам об обновлении курса (`lms.tasks.send_course_update_notification`)
отправляются по мере необходимости — сразу после сохранения изменений,
если с прошлой рассылки по этому курсу прошло больше 4 часов.

## Документация API

После запуска сервера документация доступна по адресам (замените
`localhost` на IP сервера при удалённом развёртывании):

- Swagger UI: `http://localhost/api/docs/`
- Redoc: `http://localhost/api/redoc/`
- OpenAPI-схема: `http://localhost/api/schema/`

## Основные эндпоинты

| Метод | Путь | Описание | Доступ |
|---|---|---|---|
| POST | `/api/token/` | Получение пары JWT-токенов (access/refresh) | Открыт |
| POST | `/api/token/refresh/` | Обновление access-токена | Открыт |
| POST | `/users/api/users/` | Регистрация нового пользователя | Открыт |
| GET | `/users/api/users/<id>/` | Профиль пользователя (полный — себе, публичный — чужой) | Авторизован |
| PATCH/DELETE | `/users/api/users/<id>/` | Редактирование/удаление своего профиля | Владелец |
| GET | `/users/api/payments/` | Список платежей (фильтрация, сортировка по дате) | Авторизован |
| POST | `/users/api/payments/create/` | Создать платёж и Stripe-сессию оплаты | Авторизован |
| GET | `/users/api/payments/<id>/status/` | Статус оплаты по Stripe-сессии | Владелец платежа |
| GET/POST | `/lms/courses/` | Список / создание курсов | Авторизован (создание — не модератор) |
| GET/PUT/PATCH/DELETE | `/lms/courses/<id>/` | Просмотр/редактирование/удаление курса | Владелец или модератор (удаление — только владелец) |
| GET/POST | `/lms/lessons/` | Список своих уроков / создание урока | Авторизован (создание — не модератор) |
| GET/PUT/PATCH/DELETE | `/lms/lessons/<id>/` | Просмотр/редактирование/удаление урока | Владелец или модератор (удаление — только владелец) |
| POST | `/lms/subscribe/` | Подписка/отписка от обновлений курса (toggle) | Авторизован |
| \* | `/admin/` | Django-админка | Staff |

Помимо API, есть классический веб-интерфейс на Django-шаблонах: регистрация,
вход, сброс пароля, просмотр списков курсов/уроков (`/lms/web/...`) и их
редактирование для сотрудников (`is_staff`).

## Модели

**Course** (`lms/models.py`): `title`, `preview`, `description`, `owner`,
`updated_at`, `last_notified_at`.

**Lesson** (`lms/models.py`): `course`, `title`, `description`, `preview`,
`video_url`, `owner`. Ссылка `video_url` проходит валидацию — принимаются
только ссылки на `youtube.com`.

**Payment** (`users/models.py`): `user`, `payment_date`, `paid_course` /
`paid_lesson`, `amount`, `payment_method` (`cash` / `transfer`),
`session_id` и `payment_link` (данные Stripe-сессии).

**Subscription** (`users/models.py`): `user`, `course`, `created_at` —
уникальная пара `(user, course)`.

### Права доступа

- Создавать курсы и уроки может любой авторизованный пользователь, кроме
  модератора.
- Редактировать чужой курс/урок может владелец либо пользователь из
  группы `moderators`.
- Удалять курс/урок может только владелец — даже модератор не может.
- Список уроков возвращает либо все уроки (модератору), либо только свои
  (обычному пользователю).
- Профиль пользователя: себе видно всё (включая платежи), чужой профиль —
  только публичные поля; редактировать можно только свой профиль.

## Структура проекта

```
config/          настройки Django, Celery, корневые urls
lms/             курсы, уроки, подписки, права доступа, celery-задачи
users/           кастомная модель пользователя, платежи (Stripe), JWT-авторизация
templates/       шаблоны веб-интерфейса (регистрация, вход, курсы, уроки)
```

---

## Развёртывание: сервер, Docker и GitHub Actions CI/CD

Пошаговый гайд для настройки удалённого сервера и автоматического деплоя
через GitHub Actions. Архитектура: Nginx (reverse-proxy, единственный
сервис наружу) → Gunicorn внутри контейнера `web` → PostgreSQL и Redis
(доступны только внутри Docker-сети). Celery и Celery Beat — фоновые
воркеры без внешнего доступа.

Все команды на сервере выполняются от вашего обычного пользователя с
`sudo` (root-доступ отдельно не создаём и не используем).

---

### Содержание

1. [Настройка сервера](#1-настройка-сервера)
2. [Изменения в репозитории проекта](#2-изменения-в-репозитории-проекта)
3. [Настройка GitHub Secrets](#3-настройка-github-secrets)
4. [GitHub Actions workflow](#4-github-actions-workflow)
5. [Первый деплой и проверка](#5-первый-деплой-и-проверка)
6. [Как это работает при следующих push](#6-как-это-работает-при-следующих-push)
7. [Типичные проблемы](#7-типичные-проблемы)
8. [Чек-лист перед сдачей](#8-чек-лист-перед-сдачей)

---

### 1. Настройка сервера

Всё выполняется один раз, вручную, по SSH.

#### 1.1. Установите Docker и Docker Compose

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Перелогиньтесь (`exit`, затем зайдите заново по SSH) — иначе членство в
группе `docker` не применится и команды `docker compose` будут требовать
`sudo`.

Включите автозапуск Docker при перезагрузке сервера (это закрывает
критерий «авто-перезапуск» на уровне ОС — контейнеры сами поднимутся
после ребута благодаря `restart: unless-stopped` в `docker-compose.yml`):

```bash
sudo systemctl enable docker
```

Проверьте, что всё встало:

```bash
docker --version
docker compose version
```

#### 1.2. Сгенерируйте отдельный SSH-ключ для GitHub Actions

Не используйте свой личный ключ для CI/CD — заведите отдельный,
предназначенный только для деплоя:

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/gh_deploy_key -N ""
cat ~/.ssh/gh_deploy_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Выведите приватный ключ и скопируйте его целиком (вместе со строками
`-----BEGIN OPENSSH PRIVATE KEY-----` и `-----END OPENSSH PRIVATE KEY-----`):

```bash
cat ~/.ssh/gh_deploy_key
```

Он понадобится на шаге 3 — это будет секрет `SSH_PRIVATE_KEY` в GitHub.

#### 1.3. Отключите вход по паролю и root-доступ

Откройте конфиг:

```bash
sudo nano /etc/ssh/sshd_config
```

Убедитесь, что выставлено:

```
PasswordAuthentication no
PermitRootLogin no
```

Перезапустите SSH:

```bash
sudo systemctl restart ssh
```

**Важно:** прежде чем закрывать текущую SSH-сессию, откройте **новое**
окно терминала и убедитесь, что вход по ключу действительно работает.
Если сейчас ошибиться и закрыть единственную рабочую сессию, доступ к
серверу можно потерять полностью (без доступа к консоли хостинг-провайдера
восстановить будет сложно).

#### 1.4. Настройте firewall (ufw)

```bash
sudo apt update && sudo apt install -y ufw
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw enable
sudo ufw status
```

Вывод `ufw status` должен показать разрешёнными только `22/tcp` (SSH) и
`80/tcp` (HTTP через Nginx). Порты PostgreSQL (5432), Redis (6379) и
gunicorn (8000) **не открываем** — в `docker-compose.yml` они объявлены
через `expose`, а не `ports`, то есть физически недоступны снаружи сервера,
firewall тут для второго слоя защиты.

#### 1.5. Склонируйте репозиторий на сервер

```bash
git clone <URL-вашего-репозитория> ~/LMS_System
cd ~/LMS_System
```

Это разовое действие. Дальше GitHub Actions будет сам обновлять код в
этой же папке командой `git fetch` + `git reset --hard` при каждом деплое
— повторно клонировать вручную не нужно.

---

### 2. Изменения в репозитории проекта

Внесите эти файлы/правки в свой репозиторий **до** первого запуска
workflow.

#### 2.1. `config/settings.py` — вынести DEBUG и ALLOWED_HOSTS в переменные окружения

Сейчас в проекте:

```python
DEBUG = True
ALLOWED_HOSTS = []
```

С `ALLOWED_HOSTS = []` Django откажет в обслуживании запросов на внешний
IP (ответит `400 Bad Request: DisallowedHost`). `DEBUG = True` в проде —
угроза безопасности: при любой ошибке 500 в ответе будет полный traceback
с путями на сервере и содержимым переменных окружения.

Замените на:

```
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h.strip()]
```

#### 2.2. `docker-compose.yml` — добавить Nginx, закрыть прямой доступ к web

Замените файл в корне проекта на:

```yaml
services:

  db:
    image: postgres:16-alpine
    restart: unless-stopped
    env_file:
      - .env
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    expose:
      - "5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --save 60 1 --appendonly yes
    volumes:
      - redis_data:/data
    expose:
      - "6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  # Django-приложение (gunicorn) — команда запуска берётся из CMD в Dockerfile.
  # Наружу НЕ публикуется — доступ есть только у nginx внутри Docker-сети.
  web:
    build: .
    restart: unless-stopped
    env_file:
      - .env
    environment:
      DB_HOST: db
      DB_PORT: 5432
      REDIS_HOST: redis
      REDIS_PORT: 6379
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    expose:
      - "8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery:
    build: .
    restart: unless-stopped
    command: celery -A config worker --loglevel=info
    env_file:
      - .env
    environment:
      DB_HOST: db
      DB_PORT: 5432
      REDIS_HOST: redis
      REDIS_PORT: 6379
    volumes:
      - media_volume:/app/media
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      web:
        condition: service_started

  celery-beat:
    build: .
    restart: unless-stopped
    command: celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    env_file:
      - .env
    environment:
      DB_HOST: db
      DB_PORT: 5432
      REDIS_HOST: redis
      REDIS_PORT: 6379
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      web:
        condition: service_started

  # Nginx — единственный сервис, открытый наружу. Раздаёт статику/медиа
  # напрямую и проксирует остальные запросы в gunicorn (web:8000).
  nginx:
    image: nginx:1.27-alpine
    restart: unless-stopped
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - static_volume:/app/staticfiles:ro
      - media_volume:/app/media:ro
    ports:
      - "80:80"
    depends_on:
      - web

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

#### 2.3. `nginx/default.conf` — создать новый файл

```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 20M;

    location /static/ {
        alias /app/staticfiles/;
    }

    location /media/ {
        alias /app/media/;
    }

    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 2.4. `.env.template` — обновить

```env
SECRET_KEY=

DEBUG=False
ALLOWED_HOSTS=

DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=db
DB_PORT=5432

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

DEFAULT_FROM_EMAIL=noreply@lms.com
STRIPE_SECRET_KEY=
```

Настоящий `.env` на сервере коммитить **не нужно** — он будет создаваться
автоматически на каждом деплое прямо из GitHub Secrets (см. раздел 4).
Убедитесь, что `.env` присутствует в `.gitignore`.

#### 2.5. `.github/workflows/ci-cd.yml` — создать workflow

Файл целиком приведён в разделе 4.

#### 2.6. Структура файлов после всех правок

```
LMS_System/
├── config/
│   └── settings.py          ← правка (2.1)
├── nginx/
│   └── default.conf         ← новый файл (2.3)
├── .github/
│   └── workflows/
│       └── ci-cd.yml        ← новый файл (2.5)
├── docker-compose.yml       ← заменить (2.2)
├── .env.template            ← заменить (2.4)
├── Dockerfile
├── requirements.txt
└── .gitignore
```

---

### 3. Настройка GitHub Secrets

В репозитории: **Settings → Secrets and variables → Actions → New
repository secret**. Добавьте каждый из них:

| Secret | Значение |
|---|---|
| `SSH_HOST` | IP вашего сервера |
| `SSH_USER` | ваш пользователь на сервере (тот, под которым клонировали репозиторий) |
| `SSH_PORT` | обычно `22` |
| `SSH_PRIVATE_KEY` | содержимое `~/.ssh/gh_deploy_key` целиком (см. шаг 1.2) |
| `DJANGO_SECRET_KEY` | новый секретный ключ Django для продакшна (не тот, что для разработки) |
| `SERVER_IP` | тот же IP, что и в `SSH_HOST` — пойдёт в `ALLOWED_HOSTS` |
| `DB_NAME` | имя продакшн-базы, например `lms_system` |
| `DB_USER` | пользователь продакшн-БД |
| `DB_PASSWORD` | пароль продакшн-БД (сгенерируйте новый, не берите из dev) |
| `STRIPE_SECRET_KEY` | ключ Stripe (тестовый или боевой) |

Сгенерировать новый `SECRET_KEY` для Django можно локально:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

### 4. GitHub Actions workflow

Создайте файл `.github/workflows/ci-cd.yml`:

```yaml
name: CI/CD

on:
  push:
    branches: [ develop ]
  pull_request:
    branches: [ develop ]

jobs:

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install flake8
        run: pip install flake8

      - name: Run flake8
        run: flake8 .

  test:
    needs: lint
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 5

    env:
      SECRET_KEY: test-secret-key
      DEBUG: "True"
      ALLOWED_HOSTS: "localhost,127.0.0.1"
      DB_NAME: test_db
      DB_USER: test_user
      DB_PASSWORD: test_password
      DB_HOST: localhost
      DB_PORT: 5432
      REDIS_HOST: localhost
      REDIS_PORT: 6379
      REDIS_DB: 0
      STRIPE_SECRET_KEY: sk_test_dummy

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: python manage.py test

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t lms-system:${{ github.sha }} .

  deploy:
    needs: build
    if: github.ref == 'refs/heads/develop' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          port: ${{ secrets.SSH_PORT }}
          script: |
            set -e
            cd ~/LMS_System

            git fetch origin develop
            git reset --hard origin/develop

            cat > .env << 'EOF'
            SECRET_KEY=${{ secrets.DJANGO_SECRET_KEY }}
            DEBUG=False
            ALLOWED_HOSTS=${{ secrets.SERVER_IP }}
            DB_NAME=${{ secrets.DB_NAME }}
            DB_USER=${{ secrets.DB_USER }}
            DB_PASSWORD=${{ secrets.DB_PASSWORD }}
            DB_HOST=db
            DB_PORT=5432
            REDIS_HOST=redis
            REDIS_PORT=6379
            REDIS_DB=0
            DEFAULT_FROM_EMAIL=noreply@lms.com
            STRIPE_SECRET_KEY=${{ secrets.STRIPE_SECRET_KEY }}
            EOF

            docker compose down
            docker compose up --build -d
```

#### Как устроен pipeline

| Этап | Что делает | Что произойдёт при ошибке |
|---|---|---|
| `lint` | `flake8 .` — проверка стиля кода | Pipeline остановится, `test` не запустится |
| `test` | `python manage.py test` с реальными Postgres/Redis (сервисы GitHub Actions) | Pipeline остановится, `build` не запустится |
| `build` | `docker build` — проверка, что образ вообще собирается | Pipeline остановится, `deploy` не запустится |
| `deploy` | Только для push в `develop`. По SSH обновляет код и пересобирает контейнеры на сервере | — |

`needs: <job>` в каждом job гарантирует последовательность: следующий
этап не запустится, пока предыдущий не завершится успешно.

Для Pull Request в `develop` выполнятся только `lint`, `test` и `build` —
`deploy` не сработает (условие `if: github.event_name == 'push'`),
поэтому мёржить можно только то, что реально собирается и проходит тесты,
но сам сервер PR-ом не трогается.

---

### 5. Первый деплой и проверка

#### 5.1. Перед тем как пушить — локальная самопроверка

Прежде чем отдавать код в CI, стоит убедиться, что базовые вещи не
сломаны локально — так вы не тратите циклы workflow на очевидные ошибки:

```bash
flake8 .                     # то же самое, что прогонит job "lint"
python manage.py test        # то же самое, что прогонит job "test"
docker build -t lms-test .   # то же самое, что прогонит job "build"
```

Если что-то из этого падает локально — оно упадёт и в CI, только вы
узнаете об этом на 2 минуты раньше, а не после ожидания раннера GitHub.

#### 5.2. Закоммитьте и запушьте

```bash
git add .
git commit -m "Настройка деплоя: Nginx, Docker Compose, GitHub Actions CI/CD"
git push origin <ваша-ветка-дз>
```

Откройте PR из ветки ДЗ в `develop`. На этом этапе запустятся только
`lint`, `test` и `build` — `deploy` не сработает для PR (сработает только
на реальный push в `develop`, то есть после мёржа).

#### 5.3. Смотрим вкладку Actions — пошагово

Зайдите в репозиторий на GitHub → вкладка **Actions**. Вы увидите список
запусков workflow — самый свежий будет наверху, с жёлтым кружком (идёт)
или зелёной галочкой / красным крестиком (завершён).

1. Кликните на текущий запуск.
2. Слева будет граф из 4 job'ов: `lint → test → build → deploy`. Они
   выполняются последовательно (это и обеспечивает `needs:`).
3. Кликните на любой job — справа развернётся список шагов с логами.
4. Если job упал — раскройте именно тот шаг, где стоит красный крестик
   (не обязательно последний), там будет полный вывод ошибки — та же
   информация, что вы видели бы в терминале локально.

**Частые причины падения на каждом этапе:**

- `lint` красный → `flake8` нашёл нарушения стиля. В логе будет список
  файлов и строк — поправьте и запушьте снова.
- `test` красный → смотрите traceback в логе. Отдельно обратите внимание,
  не связана ли ошибка с переменными окружения (`DisallowedHost`,
  `OperationalError` — БД/Redis сервисы GitHub Actions ещё не готовы или
  не совпадают с блоком `env:` в workflow).
- `build` красный → та же ошибка, что вы бы увидели у себя при
  `docker build .` — чаще всего проблема в `requirements.txt` (см. раздел
  7 гайда о `psycopg2` из предыдущей переписки — эта же категория ошибок).
- `deploy` красный → почти всегда SSH-проблема (неверный секрет,
  ключ не добавлен на сервере) либо ошибка внутри `docker compose up`
  на сервере — полный вывод команды виден прямо в логе шага `Deploy to
  server via SSH`.

#### 5.4. После того как деплой прошёл (все 4 галочки зелёные)

Первым делом — сырая проверка, что сайт вообще отвечает:

```bash
curl -I http://<IP-сервера>/
```

Ожидаемый ответ — строка вида `HTTP/1.1 200 OK` (или `301`/`302`, если
Django что-то редиректит). Если вместо этого `curl` виснет или пишет
`Connection refused` — проблема на уровне сети/firewall/nginx, идите в
раздел 5.5. Если приходит `400 Bad Request` — почти наверняка не
подхватился `ALLOWED_HOSTS`, идите в раздел 5.6.

Дальше — откройте в браузере:

- `http://<IP-сервера>/` — главная страница.
- `http://<IP-сервера>/api/docs/` — Swagger UI.
- `http://<IP-сервера>/admin/` — страница входа в админку (пока без
  доступа — суперпользователя ещё не создали, см. 5.9).

#### 5.5. Если сайт не отвечает вообще — диагностика по шагам

Зайдите на сервер:

```bash
ssh <ваш_пользователь>@<IP-сервера>
cd ~/LMS_System
```

Проверьте статус контейнеров:

```bash
docker compose ps
```

Ожидаемая картина — 6 сервисов, у каждого статус `Up` (для `db`/`redis`
дополнительно `(healthy)`):

```
NAME                       STATUS
lms_system-db-1            Up 5 minutes (healthy)
lms_system-redis-1         Up 5 minutes (healthy)
lms_system-web-1           Up 5 minutes
lms_system-celery-1        Up 5 minutes
lms_system-celery-beat-1   Up 5 minutes
lms_system-nginx-1         Up 5 minutes
```

Если какого-то контейнера нет в списке или он в статусе `Restarting` —
смотрите его логи:

```bash
docker compose logs nginx --tail=50
docker compose logs web --tail=50
```

Если контейнеры все `Up`, а `curl` снаружи не проходит — проблема не в
Docker, а в сети сервера:

```bash
sudo ufw status verbose
```

Убедитесь, что `80/tcp` разрешён. Если у вас облачный провайдер
(Timeweb, Selectel, AWS, Yandex Cloud и т.п.) — у него часто есть **свой**
firewall на уровне панели управления (Security Group / Файрвол ВМ),
отдельный от `ufw` внутри самой машины. Проверьте и его — это самая
частая причина "контейнеры работают, а сайт всё равно недоступен".

#### 5.6. Если приходит `400 Bad Request`

Это значит Django не видит IP сервера в `ALLOWED_HOSTS`. Проверьте,
что реально записалось в `.env` на сервере (workflow пересоздаёт этот
файл при каждом деплое):

```bash
cat ~/LMS_System/.env
```

Убедитесь, что строка `ALLOWED_HOSTS=` содержит именно тот IP, по
которому вы стучитесь в браузере. Если она пустая — значит секрет
`SERVER_IP` в GitHub либо не заполнен, либо содержит опечатку. Поправьте
секрет и запустите workflow заново (Actions → на нужном запуске → кнопка
`Re-run all jobs`), либо просто сделайте пустой коммит и запушьте.

#### 5.7. Проверка, что миграции применились

`CMD` в `Dockerfile` уже прогоняет `migrate` при каждом старте `web`, но
не будет лишним убедиться:

```bash
docker compose exec web python manage.py showmigrations
```

Все миграции должны быть отмечены `[X]`. Если видите `[ ]` — что-то
пошло не так при старте контейнера `web`, смотрите:

```bash
docker compose logs web --tail=100
```

#### 5.8. Проверка статики и медиа через Nginx

```bash
curl -I http://<IP-сервера>/static/admin/css/base.css
```

Ожидается `200 OK` — это подтверждает, что `collectstatic` отработал
(в `Dockerfile`) и Nginx реально видит папку `staticfiles` через общий
volume `static_volume`. Если `404` — проверьте:

```bash
docker compose exec web ls /app/staticfiles | head
docker compose exec nginx ls /app/staticfiles | head
```

Оба вывода должны показывать одинаковое содержимое (файлы CSS/JS
Django-админки и DRF). Если у `nginx` папка пустая — проблема в
монтировании volume в `docker-compose.yml` (проверьте, что название
volume `static_volume` совпадает в секциях `web` и `nginx`).

#### 5.9. Создайте суперпользователя и группу модераторов

Разово, после первого успешного деплоя:

```bash
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py create_groups
```

Второй командой создаётся группа `moderators`, которая используется в
`permissions.py` — без неё логика прав доступа модераторов работать не
будет (не упадёт с ошибкой, просто группа будет отсутствовать, и
назначить модератора будет некому).

Проверьте вход в `http://<IP-сервера>/admin/` под созданным
суперпользователем.

#### 5.10. Проверка Celery (воркер и планировщик)

Воркер:

```bash
docker compose logs celery --tail=30
```

В логе должна быть строка вида `celery@<hostname> ready.` — значит воркер
подключился к Redis и готов принимать задачи.

Планировщик:

```bash
docker compose logs celery-beat --tail=30
```

Ищите строки `Scheduler: Sending due task block-inactive-users-daily`
(они появятся не сразу — задача запускается раз в сутки в полночь по
UTC, согласно `CELERY_BEAT_SCHEDULE` в `settings.py`). Чтобы не ждать
сутки, можно проверить, что сама таблица расписания создалась в БД —
`django_celery_beat` создаёт свои таблицы через миграции, что уже
покрыто проверкой из раздела 5.7.

Чтобы проверить воркер прямо сейчас, не дожидаясь полуночи, можно
вручную вызвать задачу из Django shell:

```bash
docker compose exec web python manage.py shell -c "from users.tasks import block_inactive_users; block_inactive_users.delay()"
```

И сразу посмотреть, забрал ли её воркер:

```bash
docker compose logs celery --tail=10
```

Там должна появиться строка о выполнении задачи `block_inactive_users`.

---

### 6. Как это работает при следующих push

При каждом `git push` в `develop` (напрямую или через мёрж PR):

1. GitHub Actions запускает `lint` → `test` → `build`.
2. Если все три прошли успешно, запускается `deploy`.
3. Workflow по SSH заходит на сервер, обновляет код (`git reset --hard
   origin/develop`), пересоздаёт `.env` из актуальных Secrets и выполняет
   `docker compose up --build -d` — это пересоберёт только те образы,
   в которых реально что-то изменилось (Docker кеширует слои), и
   перезапустит контейнеры с новым кодом.
4. `restart: unless-stopped` гарантирует, что при падении или перезагрузке
   сервера контейнеры поднимутся сами — вручную ничего перезапускать не
   нужно.

---

### 7. Типичные проблемы

| Симптом | Причина | Решение |
|---|---|---|
| `400 Bad Request` в браузере | `ALLOWED_HOSTS` не содержит IP сервера | См. раздел 5.6 |
| `curl` виснет / `Connection refused` | Порт 80 закрыт или nginx не поднялся | См. раздел 5.5 |
| `502 Bad Gateway` от Nginx | Nginx поднялся, а `web` — нет (либо ещё не прошёл миграции) | `docker compose logs web --tail=50`; проверьте, что `web` в статусе `Up`, а не `Restarting` |
| `deploy` падает с ошибкой SSH-подключения | Неверный `SSH_HOST`/`SSH_PORT`/`SSH_PRIVATE_KEY` | Проверьте секреты; убедитесь, что публичный ключ реально в `~/.ssh/authorized_keys` на сервере (`cat ~/.ssh/authorized_keys` на сервере) |
| `docker compose up` падает на сервере с `permission denied` | Нет доступа у пользователя к Docker | `groups $USER` должен содержать `docker`; если нет — повторите `usermod -aG docker $USER` и перелогиньтесь |
| Тесты падают на `DisallowedHost` в CI | Забыли переменные `DEBUG`/`ALLOWED_HOSTS` в блоке `env:` job'а `test` | Проверьте, что блок `env:` в `test` из раздела 4 скопирован полностью |
| Сайт недоступен по IP, хотя контейнеры `running` | Порт 80 закрыт в ufw, либо провайдер блокирует порт на уровне облака (Security Group) | `sudo ufw status`; для облачных провайдеров (AWS/Timeweb/Selectel и т.п.) дополнительно проверьте панель управления — там свой firewall поверх ufw |
| `git reset --hard` на сервере ругается на права | Репозиторий клонирован от другого пользователя | Убедитесь, что клонировали именно от `SSH_USER`, указанного в секретах |
| Статика/админка без CSS (`404` на `/static/...`) | `collectstatic` не отработал, либо volume между `web` и `nginx` не совпадает | См. раздел 5.8 |
| `django_celery_beat` таблиц нет / `celery-beat` падает при старте | Миграции не применились до старта `celery-beat` | Перезапустите: `docker compose restart celery-beat` уже после того, как `web` применил миграции; проверьте порядок через `depends_on` в `docker-compose.yml` |
| После ребута сервера сайт не поднялся | Docker не был в автозапуске | `sudo systemctl status docker` — если `disabled`, выполните `sudo systemctl enable docker` и `sudo systemctl start docker`, затем `docker compose up -d` в папке проекта вручную один раз |
| Workflow вообще не запускается при push | Файл лежит не по пути `.github/workflows/*.yml`, либо ошибка YAML-синтаксиса | Проверьте точный путь и отступы (YAML чувствителен к пробелам); GitHub покажет ошибку парсинга прямо во вкладке Actions, если файл невалиден |

---

### 8. Чек-лист перед сдачей

- [ ] `config/settings.py`: `DEBUG` и `ALLOWED_HOSTS` читаются из окружения
- [ ] `docker-compose.yml` содержит `nginx`, у `db`/`redis`/`web` — `expose`, не `ports`
- [ ] `nginx/default.conf` создан и проксирует на `web:8000`
- [ ] `.env` отсутствует в репозитории, есть в `.gitignore`
- [ ] `.env.template` актуален и содержит все переменные
- [ ] `.github/workflows/ci-cd.yml` создан, все 4 job'а на месте
- [ ] Все секреты добавлены в GitHub (раздел 3)
- [ ] На сервере: Docker установлен, автозапуск включён, вход по паролю и root отключены, ufw настроен
- [ ] Push в `develop` проходит все этапы pipeline и успешно деплоится
- [ ] Сайт открывается по `http://<IP-сервера>/`, `/api/docs/` работает
- [ ] `docker compose ps` на сервере показывает все сервисы healthy/running
- [ ] Коммиты в PR относятся только к этому заданию, история чистая