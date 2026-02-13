# TaskParser — Парсер задач Codeforces и Telegram бот

Проект для сбора данных о задачах с Codeforces через официальное API, их хранения в PostgreSQL и предоставления удобного интерфейса поиска через Telegram-бота. Парсинг выполняется автоматически каждый час.

## Функциональность

1. **Парсер Codeforces API:** Собирает данные о задачах: название, номер, сложность (рейтинг), количество решений, теги (темы). Сохраняет и обновляет их в базе данных каждый час с помощью Celery Beat.

2. **Telegram-бот:**
    *   Поиск задач по названию или номеру контеста.
    *   Подборка 10 задач по выбранному диапазону сложности.
    *   Подборка 10 задач по одному или нескольким тегам.
    *   Показывает подробную информацию о задаче: ссылка на Codeforces, сложность, количество решений, все теги.

## Технологический стек

*   **Язык:** Python 3.11+
*   **Фреймворк:** Django 5.1 (для административной панели и структуры), Django REST Framework
*   **База данных:** PostgreSQL 15
*   **ORM:** SQLAlchemy 2.0 (для работы с данными парсера)
*   **Асинхронные задачи:** Celery 5.3 + Redis 7 (брокер)
*   **Telegram бот:** python-telegram-bot 20.x
*   **Контейнеризация:** Docker, Docker Compose
*   **Тестирование:** Pytest

## Быстрый старт

### Локальный запуск (без Docker)

```bash
# Клонировать репозиторий
git clone https://github.com/Galaxy-Voyager/TaskParser.git
cd TaskParser

# Установить зависимости (используется Poetry)
poetry install

# Активировать окружение
poetry shell

# Настроить переменные окружения (скопировать пример)
cp .env.example .env
# Отредактировать .env, указав данные для PostgreSQL и токен бота

# Применить миграции Django
python manage.py migrate

# Запустить парсер вручную для первичной загрузки данных
python manage.py shell -c "from parser.tasks import parse_codeforces_tasks; parse_codeforces_tasks()"

# Запустить Telegram бота
python manage.py run_bot
```

### Запуск через Docker

```bash
# Клонировать репозиторий
git clone https://github.com/Galaxy-Voyager/TaskParser.git
cd TaskParser

# Создать и отредактировать .env файл (обязательно указать TELEGRAM_BOT_TOKEN)
cp .env.example .env
nano .env

# Запустить все сервисы (PostgreSQL, Redis, Django, Бот, Celery)
docker-compose up -d --build

# Проверить статус контейнеров
docker ps

# Посмотреть логи бота
docker logs taskparser_bot -f

# Запустить внеплановое обновление БД
docker exec -it taskparser_web python force_update.py
```

## Тестирование

Для запуска тестов и проверки покрытия используйте:

```bash
pytest tests/ -v --cov=. --cov-report=term
```

## Деплой на сервер

Проект полностью подготовлен для деплоя. На сервере должны быть установлены Docker и Docker Compose.

1. Скопировать файлы проекта на сервер (или использовать git clone).
2. Настроить файл `.env` с актуальными данными.
3. Запустить контейнеры: `docker-compose up -d --build`.
4. Для автоматического запуска контейнеров при старте системы выполнить:
    ```bash
    docker update --restart unless-stopped $(docker ps -q)
    sudo systemctl enable docker
    ```