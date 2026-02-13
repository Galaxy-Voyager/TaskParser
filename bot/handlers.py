"""
Telegram bot handlers for Codeforces task parser.
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

from django.conf import settings

from .database import BotDatabase
from .keyboards import (
    get_main_keyboard, get_rating_keyboard, get_tag_keyboard,
    get_selected_tags_keyboard, get_task_action_keyboard,
    get_simple_keyboard, get_confirmation_keyboard
)

logger = logging.getLogger(__name__)

# User session storage
user_sessions: Dict[int, Dict[str, Any]] = {}


class CodeforcesBotHandlers:
    """Handlers for Telegram bot commands and callbacks."""

    def __init__(self):
        """Initialize bot handlers with database connection."""
        self.db = BotDatabase()
        self.bot_token = settings.TELEGRAM_BOT_TOKEN

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /start command.
        Register user and show main menu.
        """
        user = update.effective_user

        # Save user to database
        db_user = self.db.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

        # Store user in session
        user_sessions[user.id] = {
            'user_id': db_user.id,
            'selected_tags': [],
            'selected_rating': None
        }

        welcome_text = (
            f"Привет, {user.first_name}!\n\n"
            "Я бот для поиска задач на Codeforces.\n"
            "Я помогу тебе найти задачи по сложности и темам.\n\n"
            "Что я умею:\n"
            "- Искать задачи по названию или номеру\n"
            "- Подбирать задачи по сложности\n"
            "- Фильтровать задачи по тегам\n"
            "- Показывать статистику\n\n"
            "Выбери действие в меню ниже:"
        )

        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_keyboard()
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /help command.
        Show help information.
        """
        help_text = (
            "Помощь по использованию бота\n\n"
            "Основные команды:\n"
            "/start - Запустить бота и зарегистрироваться\n"
            "/help - Показать эту справку\n"
            "/search <текст> - Поиск задач (пример: /search графы)\n"
            "/rating 800 1200 - Задачи по сложности\n"
            "/stats - Ваша статистика\n\n"
            "Как пользоваться:\n"
            "1. Выберите 'Поиск задач' для поиска по названию\n"
            "2. Выберите 'Подборка по сложности' для фильтра по рейтингу\n"
            "3. Выберите 'Поиск по тегам' для фильтра по темам\n\n"
            "Доступные теги:\n"
            "Математика, графы, динамика, жадные алгоритмы, строки, геометрия и другие\n\n"
            "Бот создан в образовательных целях\n"
            "Автор бота: @GalaxyVoyager"
        )

        await update.message.reply_text(
            help_text,
            reply_markup=get_main_keyboard()
        )

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /stats command.
        Show user statistics.
        """
        user = update.effective_user

        stats = self.db.get_user_statistics(user.id)

        if not stats:
            await update.message.reply_text(
                "Статистика пока отсутствует. Начните использовать бота!",
                reply_markup=get_main_keyboard()
            )
            return

        username = f"@{user.username}" if user.username else user.first_name

        text = (
            f"Ваша статистика\n\n"
            f"Пользователь: {username}\n"
            f"Начало использования: {stats['member_since'].strftime('%d.%m.%Y')}\n"
            f"Выполнено поисков: {stats['search_count']}\n"
        )

        if stats['favorite_tags']:
            text += f"\nЧасто искомые теги:\n"
            for tag in stats['favorite_tags'][:5]:
                if tag:
                    text += f"- {tag}\n"

        await update.message.reply_text(
            text,
            reply_markup=get_main_keyboard()
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle regular text messages.
        Process main menu commands.
        """
        user_id = update.effective_user.id
        text = update.message.text

        if user_id not in user_sessions:
            # Initialize session if not exists
            db_user = self.db.get_or_create_user(
                telegram_id=user_id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name,
                last_name=update.effective_user.last_name
            )
            user_sessions[user_id] = {
                'user_id': db_user.id,
                'selected_tags': [],
                'selected_rating': None,
                'last_message_id': None
            }

        if text == "Поиск задач":
            await update.message.reply_text(
                "Введите название задачи или номер контеста:",
                reply_markup=get_simple_keyboard()
            )
            user_sessions[user_id]['state'] = 'waiting_for_search_query'

        elif text == "Подборка по сложности":
            await update.message.reply_text(
                "Выберите диапазон сложности:",
                reply_markup=get_rating_keyboard()
            )

        elif text == "Поиск по тегам":
            # Get all tags from database
            tags = self.db.get_all_tags()
            user_sessions[user_id]['selected_tags'] = []

            if not tags:
                await update.message.reply_text(
                    "База данных задач еще не загружена. Попробуйте позже.",
                    reply_markup=get_main_keyboard()
                )
                return

            keyboard, total_pages = get_tag_keyboard(tags, 0)
            await update.message.reply_text(
                f"Выберите теги (найдено тегов: {len(tags)}):\n"
                "Можно выбрать несколько тегов. После выбора нажмите 'Готово'",
                reply_markup=keyboard
            )

        elif text == "Статистика":
            await self.stats_command(update, context)

        elif text == "Помощь":
            await self.help_command(update, context)

        elif user_sessions.get(user_id, {}).get('state') == 'waiting_for_search_query':
            # Process search query
            await self.search_tasks(update, context, text)
            user_sessions[user_id]['state'] = None

        else:
            await update.message.reply_text(
                "Пожалуйста, используйте кнопки меню.",
                reply_markup=get_main_keyboard()
            )

    async def search_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
        """
        Search tasks by query and send results.
        """
        user_id = update.effective_user.id

        # Search tasks
        tasks = self.db.search_tasks_by_query(query, limit=10)

        if not tasks:
            await update.message.reply_text(
                f"По запросу '{query}' ничего не найдено.",
                reply_markup=get_main_keyboard()
            )
            return

        # Save search history
        if user_id in user_sessions:
            self.db.save_search_history(
                user_id=user_sessions[user_id]['user_id'],
                query=query,
                results_count=len(tasks)
            )

        # Send results
        await self.send_task_list(update, tasks, f"Результаты поиска по запросу '{query}':")

    async def send_task_list(self, update: Update, tasks: List[Any], header: str):
        """
        Send list of tasks to user.
        """
        text = f"{header}\n\n"

        for i, task in enumerate(tasks[:10], 1):
            tags_str = ', '.join(task.tags[:3]) if task.tags else 'нет'
            text += (
                f"{i}. {task.contest_id}{task.index}: {task.name}\n"
                f"   Сложность: {task.rating or 'N/A'}\n"
                f"   Решена: {task.solved_count} раз\n"
                f"   Теги: {tags_str}\n"
                f"   Задача: /problem_{task.contest_id}_{task.index}\n\n"
            )

        text += "Нажмите на ссылку выше для просмотра задачи."

        await update.message.reply_text(
            text,
            reply_markup=get_main_keyboard()
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle inline keyboard callbacks.
        """
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        data = query.data

        if data == "back_to_main":
            await query.message.delete()
            await query.message.reply_text(
                "Главное меню:",
                reply_markup=get_main_keyboard()
            )

        elif data.startswith("rating_"):
            # Handle rating selection
            # data format: rating_800_1200
            parts = data.split('_')
            if len(parts) == 3:
                min_r = int(parts[1])
                max_r = int(parts[2])
                await self.handle_rating_selection(update, context, min_r, max_r)

        elif data.startswith("tag_page_"):
            # Handle tag page navigation
            page = int(data.split('_')[2])
            tags = self.db.get_all_tags()
            keyboard, _ = get_tag_keyboard(tags, page)
            await query.edit_message_reply_markup(reply_markup=keyboard)

        elif data.startswith("tag_"):
            # Handle tag selection
            tag = data[4:]
            if user_id in user_sessions:
                if tag not in user_sessions[user_id]['selected_tags']:
                    user_sessions[user_id]['selected_tags'].append(tag)

                    # Show selected tags
                    tags = self.db.get_all_tags()
                    keyboard = get_selected_tags_keyboard(
                        user_sessions[user_id]['selected_tags'],
                        tags
                    )

                    await query.edit_message_text(
                        f"Выбраны теги: {', '.join(user_sessions[user_id]['selected_tags'])}",
                        reply_markup=keyboard
                    )

        elif data == "tags_done":
            # Finish tag selection
            if user_id in user_sessions and user_sessions[user_id]['selected_tags']:
                await self.find_tasks_by_tags(update, context)
            else:
                await query.edit_message_text(
                    "Вы не выбрали ни одного тега. Хотите продолжить?",
                    reply_markup=get_confirmation_keyboard()
                )

        elif data == "find_by_tags":
            await self.find_tasks_by_tags(update, context)

        elif data.startswith("remove_tag_"):
            tag = data[11:]
            if user_id in user_sessions and tag in user_sessions[user_id]['selected_tags']:
                user_sessions[user_id]['selected_tags'].remove(tag)

                if user_sessions[user_id]['selected_tags']:
                    tags = self.db.get_all_tags()
                    keyboard = get_selected_tags_keyboard(
                        user_sessions[user_id]['selected_tags'],
                        tags
                    )
                    await query.edit_message_text(
                        f"Текущие теги: {', '.join(user_sessions[user_id]['selected_tags'])}",
                        reply_markup=keyboard
                    )
                else:
                    # No tags selected, go back to tag selection
                    tags = self.db.get_all_tags()
                    keyboard, _ = get_tag_keyboard(tags, 0)
                    await query.edit_message_text(
                        "Выберите теги:",
                        reply_markup=keyboard
                    )

        elif data == "add_more_tags":
            tags = self.db.get_all_tags()
            keyboard, _ = get_tag_keyboard(tags, 0)
            await query.edit_message_text(
                "Выберите дополнительные теги:",
                reply_markup=keyboard
            )

        elif data == "clear_tags":
            if user_id in user_sessions:
                user_sessions[user_id]['selected_tags'] = []
            tags = self.db.get_all_tags()
            keyboard, _ = get_tag_keyboard(tags, 0)
            await query.edit_message_text(
                "Теги очищены. Выберите новые теги:",
                reply_markup=keyboard
            )

        elif data == "confirm_yes":
            # User confirmed to continue without tags
            tags = self.db.get_all_tags()
            keyboard, _ = get_tag_keyboard(tags, 0)
            await query.edit_message_text(
                "Выберите теги для поиска:",
                reply_markup=keyboard
            )

        elif data == "confirm_no":
            await query.message.delete()
            await query.message.reply_text(
                "Поиск отменен.",
                reply_markup=get_main_keyboard()
            )

    async def handle_rating_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                     min_rating: int, max_rating: int):
        """
        Handle rating selection and show tasks.
        """
        query = update.callback_query
        user_id = update.effective_user.id

        # Get tasks by rating
        tasks = self.db.get_tasks_by_rating_range(min_rating, max_rating, limit=10)

        if not tasks:
            await query.edit_message_text(
                f"Задачи с рейтингом {min_rating}-{max_rating} не найдены.",
                reply_markup=get_simple_keyboard()
            )
            return

        # Save search history
        if user_id in user_sessions:
            self.db.save_search_history(
                user_id=user_sessions[user_id]['user_id'],
                min_rating=min_rating,
                max_rating=max_rating,
                results_count=len(tasks)
            )

        # Format message
        text = f"Задачи с рейтингом {min_rating}-{max_rating}\n\n"

        for i, task in enumerate(tasks[:10], 1):
            tags_str = ', '.join(task.tags[:3]) if task.tags else 'нет'
            text += (
                f"{i}. {task.contest_id}{task.index}: {task.name}\n"
                f"   Сложность: {task.rating}\n"
                f"   Решена: {task.solved_count} раз\n"
                f"   Теги: {tags_str}\n"
                f"   Задача: /problem_{task.contest_id}_{task.index}\n\n"
            )

        await query.edit_message_text(
            text,
            reply_markup=get_simple_keyboard()
        )

    async def find_tasks_by_tags(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Find tasks by selected tags.
        """
        query = update.callback_query
        user_id = update.effective_user.id

        if user_id not in user_sessions or not user_sessions[user_id]['selected_tags']:
            await query.edit_message_text(
                "Не выбрано ни одного тега.",
                reply_markup=get_main_keyboard()
            )
            return

        selected_tags = user_sessions[user_id]['selected_tags']

        # Get tasks with selected tags
        tasks = self.db.get_tasks_by_filters(
            tags=selected_tags,
            limit=10
        )

        if not tasks:
            await query.edit_message_text(
                f"Задачи с тегами {', '.join(selected_tags)} не найдены.\n"
                "Попробуйте выбрать другие теги.",
                reply_markup=get_simple_keyboard()
            )
            return

        # Save search history
        self.db.save_search_history(
            user_id=user_sessions[user_id]['user_id'],
            tags=selected_tags,
            results_count=len(tasks)
        )

        # Format message
        text = f"Задачи с тегами: {', '.join(selected_tags)}\n\n"

        for i, task in enumerate(tasks[:10], 1):
            tags_str = ', '.join(task.tags[:3]) if task.tags else 'нет'
            text += (
                f"{i}. {task.contest_id}{task.index}: {task.name}\n"
                f"   Сложность: {task.rating or 'N/A'}\n"
                f"   Решена: {task.solved_count} раз\n"
                f"   Теги: {tags_str}\n"
                f"   Задача: /problem_{task.contest_id}_{task.index}\n\n"
            )

        await query.edit_message_text(
            text,
            reply_markup=get_simple_keyboard()
        )

    async def handle_problem_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /problem_contestId_index command.
        Show detailed problem information.
        """
        command = update.message.text
        parts = command.split('_')

        if len(parts) != 3:
            await update.message.reply_text(
                "Неверный формат команды.",
                reply_markup=get_main_keyboard()
            )
            return

        try:
            contest_id = int(parts[1])
            index = parts[2]
        except ValueError:
            await update.message.reply_text(
                "Неверный формат команды.",
                reply_markup=get_main_keyboard()
            )
            return

        # Find task in database
        from parser.models import Task
        task = self.db.db_session.query(Task).filter_by(
            contest_id=contest_id,
            index=index
        ).first()

        if not task:
            await update.message.reply_text(
                f"Задача {contest_id}{index} не найдена.",
                reply_markup=get_main_keyboard()
            )
            return

        # Format detailed information
        tags_str = ', '.join(task.tags[:10]) if task.tags else 'нет'
        if len(task.tags) > 10:
            tags_str += f" ... и еще {len(task.tags) - 10}"

        text = (
            f"{task.contest_id}{task.index}: {task.name}\n\n"
            f"Сложность: {task.rating or 'N/A'}\n"
            f"Количество решений: {task.solved_count}\n"
            f"Time Limit: {task.time_limit or 'N/A'} ms\n"
            f"Memory Limit: {task.memory_limit or 'N/A'} MB\n\n"
            f"Теги:\n{tags_str}\n"
        )

        await update.message.reply_text(
            text,
            reply_markup=get_task_action_keyboard(
                task.id, task.contest_id, task.index
            )
        )

    def run(self):
        """Run the Telegram bot."""
        if not self.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not set in environment variables")
            return

        # Create application
        application = Application.builder().token(self.bot_token).build()

        # Add handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("stats", self.stats_command))

        # Add handler for problem commands
        application.add_handler(
            MessageHandler(filters.Regex(r'^/problem_\d+_[A-Z]\d*$'), self.handle_problem_command)
        )

        # Add callback query handler
        application.add_handler(CallbackQueryHandler(self.handle_callback))

        # Add message handler
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Start bot
        logger.info("Starting Telegram bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
