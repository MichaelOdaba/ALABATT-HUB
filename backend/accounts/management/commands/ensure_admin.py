import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a superuser from environment variables if it does not already exist."

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.getenv('DJANGO_SUPERUSER_USERNAME', '').strip()
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', '').strip()
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', '').strip()

        if not username or not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    'Superuser env vars are missing. Set DJANGO_SUPERUSER_USERNAME, '
                    'DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD.'
                )
            )
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.SUCCESS(f'Superuser {username} already exists.'))
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f'Created superuser {username}.'))
