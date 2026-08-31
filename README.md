# LMS System

Backend платформы для онлайн-обучения на Django + DRF. Поддерживает JWT-аутентификацию, оплату курсов через Stripe и фоновые задачи (рассылки, деактивация неактивных пользователей) на Celery.

## Стек

- Python 3.12, Django 5.2, Django REST Framework
- PostgreSQL 16 — основная БД
- Redis 7 — брокер и result-backend для Celery
- Celery + Celery Beat — фоновые и периодические задачи
- Gunicorn — production-сервер приложения
- Docker / Docker Compose — оркестрация всех сервисов

## Быстрый запуск

1. Склонируйте репозиторий и перейдите в его корень.

2. Скопируйте пример переменных окружения и заполните своими значениями:

   ```bash
   cp .env.example .env
   ```

   Обязательно смените `secret_key` и `db_password` на собственные значения перед запуском в любом окружении, отличном от локальной разработки.

3. Соберите образы и запустите все сервисы одной командой:

   ```bash
   docker compose up --build -d
   ```

   Будут подняты 5 контейнеров:

   | Сервис | Назначение |
   |---|---|
   | `db` | PostgreSQL, хранит данные приложения |
   | `redis` | брокер сообщений и result-backend для Celery |
   | `web` | Django-приложение (миграции + collectstatic + gunicorn) |
   | `celery` | воркер, выполняющий фоновые задачи |
   | `celery-beat` | планировщик периодических задач |

4. После запуска приложение доступно на [http://localhost:8000](http://localhost:8000).

## Полезные команды

Логи конкретного сервиса:
```bash
docker compose logs -f web
```

Создать суперпользователя:
```bash
docker compose exec web python manage.py createsuperuser
```

Остановить все сервисы:
```bash
docker compose down
```

Остановить и удалить volumes (полный сброс данных БД и Redis):
```bash
docker compose down -v
```

## Переменные окружения

Все настройки читаются из файла `.env` в корне проекта (см. `.env.example`):

| Переменная | Назначение |
|---|---|
| `secret_key` | секретный ключ Django |
| `db_name`, `db_user`, `db_password` | доступы к PostgreSQL |
| `db_host`, `db_port` | адрес БД (внутри Docker — `db`/`5432`, переопределяется в `docker-compose.yml`) |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` | адрес Redis |
| `DEFAULT_FROM_EMAIL` | адрес отправителя писем |
| `STRIPE_SECRET_KEY` | секретный ключ Stripe для приёма платежей |

`db` и `redis` не публикуются наружу (`expose`, а не `ports`) — доступ к ним есть только у сервисов внутри Docker-сети. Наружу открыт только `web` на порту 8000.
