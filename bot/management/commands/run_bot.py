"""
Django command to run Telegram bot.
Run with: poetry run python manage.py run_bot
"""

from django.core.management.base import BaseCommand
from bot.handlers import CodeforcesBotHandlers


class Command(BaseCommand):
    help = 'Run Telegram bot for Codeforces task parser'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Telegram bot...'))

        try:
            bot = CodeforcesBotHandlers()
            bot.run()
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Bot stopped'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
            raise
