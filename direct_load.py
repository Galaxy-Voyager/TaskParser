from parser.codeforces_api import CodeforcesAPIClient, CodeforcesParser
from parser.models import init_db, Contest, Task, Tag
from django.conf import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

print("1. Подключение к БД...")
engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)
db_session = Session()
print("   OK")

print("2. Создание клиента API...")
client = CodeforcesAPIClient()
print("   OK")

print("3. Загрузка контестов...")
contests_data = client.get_contests()
print(f"   Получено {len(contests_data)} контестов")

print("4. Загрузка задач...")
problems_data = client.get_problems()
print(f"   Получено {len(problems_data)} задач")

print("5. Сохранение контестов...")
contest_count = 0
for contest_data in contests_data:
    contest = Contest(
        contest_id=contest_data['id'],
        name=contest_data['name'],
        type=contest_data.get('type'),
        phase=contest_data.get('phase'),
        frozen=contest_data.get('frozen', False),
        duration_seconds=contest_data.get('durationSeconds'),
        start_time_seconds=contest_data.get('startTimeSeconds'),
        relative_time_seconds=contest_data.get('relativeTimeSeconds'),
    )
    db_session.add(contest)
    contest_count += 1
    if contest_count % 100 == 0:
        db_session.flush()
        print(f"   ... {contest_count} контестов")

db_session.commit()
print(f"   Сохранено {contest_count} контестов")

print("6. Сохранение тегов...")
all_tags = set()
for problem in problems_data:
    all_tags.update(problem.get('tags', []))

tag_objects = {}
for tag_name in all_tags:
    tag = Tag(name=tag_name, slug=tag_name.lower().replace(' ', '-'))
    db_session.add(tag)
    tag_objects[tag_name] = tag

db_session.commit()
print(f"   Сохранено {len(all_tags)} тегов")

print("7. Сохранение задач...")
task_count = 0
for problem in problems_data:
    contest_id = problem.get('contestId')
    if not contest_id:
        continue
    
    solved_count = 0
    for stat in problems_data:
        if stat.get('contestId') == contest_id and stat.get('index') == problem.get('index'):
            solved_count = stat.get('solvedCount', 0)
            break
    
    task = Task(
        contest_id=contest_id,
        index=problem.get('index'),
        name=problem.get('name'),
        rating=problem.get('rating'),
        solved_count=solved_count,
        tags=problem.get('tags', []),
        time_limit=problem.get('timeLimit'),
        memory_limit=problem.get('memoryLimit')
    )
    db_session.add(task)
    task_count += 1
    if task_count % 500 == 0:
        db_session.flush()
        print(f"   ... {task_count} задач")

db_session.commit()
print(f"   Сохранено {task_count} задач")

print("\n" + "="*50)
print("ЗАГРУЗКА ЗАВЕРШЕНА")
print("="*50)
print(f"Контесты: {contest_count}")
print(f"Задачи: {task_count}")
print(f"Теги: {len(all_tags)}")
print("="*50)

db_session.close()
