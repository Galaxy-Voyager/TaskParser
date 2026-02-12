"""
Tests for bot database operations using PostgreSQL.
"""

import pytest
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from parser.models import Base, Task, Tag, UserSettings, SearchHistory, Contest
from bot.database import BotDatabase

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
def test_data(db_session):
    """Create test data in database."""
    # Add test contest
    contest = Contest(
        contest_id=1,
        name='Test Contest 1',
        phase='FINISHED'
    )
    db_session.add(contest)

    # Add tags
    tags = []
    for tag_name in ['math', 'dp', 'graphs', 'greedy']:
        tag = Tag(
            name=tag_name,
            slug=tag_name.replace(' ', '-')
        )
        db_session.add(tag)
        tags.append(tag)

    # Add tasks
    tasks = [
        Task(
            contest_id=1,
            index='A',
            name='Easy Problem',
            rating=800,
            solved_count=1000,
            tags=['math']
        ),
        Task(
            contest_id=1,
            index='B',
            name='Dynamic Problem',
            rating=1500,
            solved_count=500,
            tags=['dp']
        ),
        Task(
            contest_id=1,
            index='C',
            name='Graph Problem',
            rating=1800,
            solved_count=300,
            tags=['graphs']
        )
    ]

    for task in tasks:
        db_session.add(task)

    db_session.commit()

    return {
        'contest': contest,
        'tags': tags,
        'tasks': tasks
    }


@pytest.fixture
def bot_db(db_session):
    """Create BotDatabase instance with test session."""
    db = BotDatabase()
    db.db_session = db_session
    return db


class TestBotDatabase:
    """Test bot database interface with PostgreSQL."""

    def test_get_or_create_user(self, db_session):
        """Test user creation and retrieval."""
        from parser.models import UserSettings

        # Create new user
        user = UserSettings(
            telegram_id=12345,
            username='test_user',
            first_name='Test',
            last_name='User'
        )
        db_session.add(user)
        db_session.commit()

        assert user.telegram_id == 12345
        assert user.username == 'test_user'
        assert user.first_name == 'Test'

        # Query user
        found_user = db_session.query(UserSettings).filter_by(
            telegram_id=12345
        ).first()

        assert found_user is not None
        assert found_user.id == user.id

    def test_get_all_tags(self, db_session, test_data):
        """Test retrieving all tags."""
        tags = db_session.query(Tag.name).order_by(Tag.name).all()
        tag_names = [tag[0] for tag in tags]

        assert len(tag_names) >= 4
        assert 'math' in tag_names
        assert 'dp' in tag_names
        assert 'graphs' in tag_names
        assert 'greedy' in tag_names

    def test_get_tasks_by_filters(self, db_session, test_data):
        """Test filtering tasks by rating and tags."""
        # Filter by rating only
        tasks = db_session.query(Task).filter(
            Task.rating >= 800,
            Task.rating <= 1500
        ).order_by(Task.solved_count.desc()).limit(10).all()

        assert len(tasks) == 2
        assert tasks[0].rating == 800
        assert tasks[1].rating == 1500

        # Filter by tags
        tasks = db_session.query(Task).filter(
            Task.tags.contains(['math'])
        ).order_by(Task.solved_count.desc()).limit(10).all()

        assert len(tasks) == 1
        assert tasks[0].index == 'A'

    def test_search_tasks_by_query(self, db_session, test_data):
        """Test searching tasks by query."""
        # Search by contest ID
        tasks = db_session.query(Task).filter(
            Task.contest_id == 1
        ).order_by(Task.solved_count.desc()).limit(10).all()

        assert len(tasks) == 3

        # Search by name
        tasks = db_session.query(Task).filter(
            Task.name.ilike('%Easy%')
        ).order_by(Task.solved_count.desc()).limit(10).all()

        assert len(tasks) == 1
        assert tasks[0].name == 'Easy Problem'

    def test_save_search_history(self, db_session):
        """Test saving search history."""
        from parser.models import UserSettings, SearchHistory

        # Create user
        user = UserSettings(telegram_id=12345)
        db_session.add(user)
        db_session.commit()

        # Save search
        history = SearchHistory(
            user_id=user.id,
            query='test',
            min_rating=800,
            max_rating=1200,
            tags=['math'],
            results_count=5
        )
        db_session.add(history)
        db_session.commit()

        # Verify
        saved_history = db_session.query(SearchHistory).filter_by(
            user_id=user.id
        ).first()

        assert saved_history is not None
        assert saved_history.query == 'test'
        assert saved_history.min_rating == 800
        assert saved_history.max_rating == 1200
        assert saved_history.tags == ['math']
        assert saved_history.results_count == 5

    def test_get_user_statistics(self, db_session):
        """Test getting user statistics."""
        from parser.models import UserSettings, SearchHistory

        # Create user
        user = UserSettings(telegram_id=12345)
        db_session.add(user)
        db_session.commit()

        # Add search history
        for i in range(3):
            history = SearchHistory(
                user_id=user.id,
                query=f'test{i}',
                results_count=5
            )
            db_session.add(history)

        history2 = SearchHistory(
            user_id=user.id,
            tags=['math'],
            results_count=3
        )
        db_session.add(history2)
        db_session.commit()

        # Get statistics
        search_count = db_session.query(SearchHistory).filter_by(
            user_id=user.id
        ).count()

        assert search_count == 4
        assert user.telegram_id == 12345
        assert user.created_at is not None
