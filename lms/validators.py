from rest_framework import serializers


class YoutubeLinkValidator:

    ALLOWED_DOMAIN = 'youtube.com'

    def __init__(self, field):
        self.field = field

    def __call__(self, attrs):
        link = attrs.get(self.field)
        if not link:
            return
        if self.ALLOWED_DOMAIN not in link:
            raise serializers.ValidationError(
                {self.field: f'Ссылки разрешены только на {self.ALLOWED_DOMAIN}.'}
            )