from parser.codeforces_api import CodeforcesAPIClient, CodeforcesParser
from parser.models import init_db
from django.conf import settings
import sys
import traceback

print("=== ТЕСТ ПАРСЕРА ===")

try:
    print("1. Подключение к БД...")
    db_session = init_db(settings.DATABASE_URL)
    print("   OK")
except Exception as e:
    print(f"   ОШИБКА: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("2. Создание клиента API...")
    client = CodeforcesAPIClient()
    print("   OK")
except Exception as e:
    print(f"   ОШИБКА: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("3. Запрос контестов...")
    contests = client.get_contests()
    print(f"   Получено {len(contests)} контестов")
except Exception as e:
    print(f"   ОШИБКА: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("4. Запрос задач...")
    problems = client.get_problems()
    print(f"   Получено {len(problems)} задач")
except Exception as e:
    print(f"   ОШИБКА: {e}")
    traceback.print_exc()
    sys.exit(1)

print("=== ТЕСТ ПРОЙДЕН ===")
db_session.close()
