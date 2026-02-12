"""
Tests for Telegram bot handlers.
"""

import pytest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, Message, CallbackQuery, User, Chat
from telegram.ext import ContextTypes

from bot.handlers import CodeforcesBotHandlers
from bot.database import BotDatabase
from parser.models import UserSettings, Task, Tag, Base

# Load environment variables
load_dotenv()


@pytest.fixture(scope='session')
def engine():
    """Create PostgreSQL engine for testing."""
    database_url = os.environ.get(
        'TEST_DATABASE_URL',
        'postgresql://taskparser:1357@localhost:5432/taskparser_test'
    )

    engine = create_engine(database_url)

    # Create tables
    Base.metadata.drop_all(engine)  # Clean start
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(engine):
    """Create a new database session for a test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def bot_handlers(db_session):
    """Create bot handlers with mocked database."""
    handlers = CodeforcesBotHandlers()
    handlers.db = Mock(spec=BotDatabase)
    handlers.db.db_session = db_session
    return handlers


@pytest.fixture
def mock_update():
    """Create mock Telegram update."""
    update = Mock(spec=Update)
    update.effective_user = Mock(spec=User)
    update.effective_user.id = 12345
    update.effective_user.username = "test_user"
    update.effective_user.first_name = "Test"
    update.effective_user.last_name = "User"

    update.message = Mock(spec=Message)
    update.message.reply_text = AsyncMock()
    update.message.delete = AsyncMock()

    update.callback_query = Mock(spec=CallbackQuery)
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.edit_message_reply_markup = AsyncMock()
    update.callback_query.message = Mock(spec=Message)
    update.callback_query.message.delete = AsyncMock()
    update.callback_query.message.reply_text = AsyncMock()

    return update


@pytest.fixture
def mock_context():
    """Create mock context."""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    return context


class TestBotHandlers:
    """Test Telegram bot handlers."""

    @pytest.mark.asyncio
    async def test_start_command(self, bot_handlers, mock_update, mock_context):
        """Test /start command."""
        # Mock database
        bot_handlers.db.get_or_create_user.return_value = UserSettings(
            id=1,
            telegram_id=12345,
            username="test_user"
        )

        await bot_handlers.start(mock_update, mock_context)

        # Verify
        bot_handlers.db.get_or_create_user.assert_called_once_with(
            telegram_id=12345,
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        mock_update.message.reply_text.assert_called_once()
        assert "Привет, Test!" in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_help_command(self, bot_handlers, mock_update, mock_context):
        """Test /help command."""
        await bot_handlers.help_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        assert "Помощь по использованию бота" in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_stats_command_no_stats(self, bot_handlers, mock_update, mock_context):
        """Test /stats command when user has no stats."""
        bot_handlers.db.get_user_statistics.return_value = {}

        await bot_handlers.stats_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        assert "Статистика пока отсутствует" in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_stats_command_with_stats(self, bot_handlers, mock_update, mock_context):
        """Test /stats command with user statistics."""
        from datetime import datetime

        bot_handlers.db.get_user_statistics.return_value = {
            'user': UserSettings(telegram_id=12345),
            'search_count': 10,
            'favorite_tags': ['math', 'dp'],
            'member_since': datetime(2026, 1, 1)
        }

        await bot_handlers.stats_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Ваша статистика" in call_args
        assert "Выполнено поисков: 10" in call_args
        assert "math" in call_args
        assert "dp" in call_args

    @pytest.mark.asyncio
    async def test_handle_message_search_query(self, bot_handlers, mock_update, mock_context):
        """Test handling search query message."""
        from bot.handlers import user_sessions

        user_sessions[12345] = {
            'user_id': 1,
            'state': 'waiting_for_search_query'
        }

        mock_update.message.text = "watermelon"

        # Mock search results
        mock_task = Mock(spec=Task)
        mock_task.contest_id = 4
        mock_task.index = "A"
        mock_task.name = "Watermelon"
        mock_task.rating = 800
        mock_task.solved_count = 665352
        mock_task.tags = ["brute force", "math"]

        bot_handlers.db.search_tasks_by_query.return_value = [mock_task]

        # Mock send_task_list
        bot_handlers.send_task_list = AsyncMock()

        await bot_handlers.handle_message(mock_update, mock_context)

        bot_handlers.db.search_tasks_by_query.assert_called_once_with("watermelon", limit=10)
        bot_handlers.send_task_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_callback_rating(self, bot_handlers, mock_update, mock_context):
        """Test rating callback."""
        mock_update.callback_query.data = "rating_800_1200"

        # Mock handle_rating_selection
        bot_handlers.handle_rating_selection = AsyncMock()

        await bot_handlers.handle_callback(mock_update, mock_context)

        mock_update.callback_query.answer.assert_called_once()
        bot_handlers.handle_rating_selection.assert_called_once_with(
            mock_update, mock_context, 800, 1200
        )

    @pytest.mark.asyncio
    async def test_handle_callback_tag_selection(self, bot_handlers, mock_update, mock_context):
        """Test tag selection callback."""
        from bot.handlers import user_sessions

        user_sessions[12345] = {
            'user_id': 1,
            'selected_tags': []
        }

        mock_update.callback_query.data = "tag_math"
        bot_handlers.db.get_all_tags.return_value = ["math", "dp", "graphs"]

        await bot_handlers.handle_callback(mock_update, mock_context)

        assert "math" in user_sessions[12345]['selected_tags']
        mock_update.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_rating_selection(self, bot_handlers, mock_update, mock_context):
        """Test rating selection handler."""
        mock_task = Mock(spec=Task)
        mock_task.contest_id = 4
        mock_task.index = "A"
        mock_task.name = "Watermelon"
        mock_task.rating = 800
        mock_task.solved_count = 665352
        mock_task.tags = ["math"]

        bot_handlers.db.get_tasks_by_rating_range.return_value = [mock_task]

        await bot_handlers.handle_rating_selection(
            mock_update, mock_context, 800, 1200
        )

        bot_handlers.db.get_tasks_by_rating_range.assert_called_once_with(800, 1200, limit=10)
        mock_update.callback_query.edit_message_text.assert_called_once()

        call_args = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "Задачи с рейтингом 800-1200" in call_args
        assert "Watermelon" in call_args

    @pytest.mark.asyncio
    async def test_find_tasks_by_tags(self, bot_handlers, mock_update, mock_context):
        """Test finding tasks by selected tags."""
        from bot.handlers import user_sessions

        user_sessions[12345] = {
            'user_id': 1,
            'selected_tags': ['math']
        }

        mock_task = Mock(spec=Task)
        mock_task.contest_id = 4
        mock_task.index = "A"
        mock_task.name = "Watermelon"
        mock_task.rating = 800
        mock_task.solved_count = 665352
        mock_task.tags = ["math"]

        bot_handlers.db.get_tasks_by_filters.return_value = [mock_task]

        await bot_handlers.find_tasks_by_tags(mock_update, mock_context)

        bot_handlers.db.get_tasks_by_filters.assert_called_once_with(
            tags=['math'], limit=10
        )
        mock_update.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_problem_command(self, bot_handlers, mock_update, mock_context):
        """Test /problem command."""
        mock_update.message.text = "/problem_4_A"

        mock_task = Mock(spec=Task)
        mock_task.id = 1
        mock_task.contest_id = 4
        mock_task.index = "A"
        mock_task.name = "Watermelon"
        mock_task.rating = 800
        mock_task.solved_count = 665352
        mock_task.tags = ["math", "brute force"]
        mock_task.time_limit = 1000
        mock_task.memory_limit = 256

        mock_query = Mock()
        mock_filtered = Mock()

        # Настраиваем цепочку вызовов
        mock_query.filter_by.return_value = mock_filtered
        mock_filtered.first.return_value = mock_task

        # Присваиваем мок методу query
        bot_handlers.db.db_session.query = Mock(return_value=mock_query)

        await bot_handlers.handle_problem_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "4A: Watermelon" in call_args
        assert "Сложность: 800" in call_args
        assert "Количество решений: 665352" in call_args  # ИСПРАВЛЕНО
        assert "math" in call_args
        assert "brute force" in call_args
