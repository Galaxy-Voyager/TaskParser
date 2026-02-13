from parser.codeforces_api import CodeforcesParser
from parser.models import init_db
from django.conf import settings
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

print("Подключение к БД...")
db_session = init_db(settings.DATABASE_URL)

print("Запуск парсера...")
parser = CodeforcesParser(db_session)
stats = parser.parse_and_save_all()

print(f"\nГотово!")
print(f"   Контестов добавлено: {stats['contests_added']}")
print(f"   Задач добавлено: {stats['tasks_added']}")
print(f"   Задач обновлено: {stats['tasks_updated']}")

db_session.close()