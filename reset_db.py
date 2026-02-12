from sqlalchemy import create_engine, text
from django.conf import settings
from parser.models import Base
from parser.codeforces_api import CodeforcesParser
from parser.models import init_db
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("DROP SCHEMA public CASCADE;"))
    conn.commit()

with engine.connect() as conn:
    conn.execute(text("CREATE SCHEMA public;"))
    conn.commit()

with engine.connect() as conn:
    conn.execute(text("GRANT ALL ON SCHEMA public TO taskparser;"))
    conn.commit()

print("Таблицы удалены")

Base.metadata.create_all(engine)
print("Таблицы созданы")

db_session = init_db(settings.DATABASE_URL)
parser = CodeforcesParser(db_session)
stats = parser.parse_and_save_all()

print(f"Контесты: {stats['contests_added']}")
print(f"Задачи: {stats['tasks_added']}")
print(f"Теги: {stats['tags_added']}")

db_session.close()
print("Готово!")
