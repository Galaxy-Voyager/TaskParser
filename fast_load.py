from parser.codeforces_api import CodeforcesParser
from parser.models import init_db
from django.conf import settings

print("1. Подключение к БД...")
db_session = init_db(settings.DATABASE_URL)
print("   OK")

print("2. Создание парсера...")
parser = CodeforcesParser(db_session)
print("   OK")

print("3. Загрузка данных с Codeforces API...")
print("   Это займет 2-3 минуты...")
stats = parser.parse_and_save_all()

print("\n" + "="*50)
print("ПАРСИНГ ЗАВЕРШЕН")
print("="*50)
print(f"Контесты: {stats['contests_added']}")
print(f"Задачи: {stats['tasks_added']}")
print(f"Теги: {stats['tags_added']}")
print("="*50)

db_session.close()
print("4. Готово!")
