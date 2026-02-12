"""
SQLAlchemy models for Codeforces tasks parser.
These models are independent from Django ORM.
"""

from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text,
    DateTime, Table, ForeignKey, Index, Float, Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.dialects.postgresql import ARRAY

Base = declarative_base()

# Association table for many-to-many relationship between tasks and tags
task_tags = Table(
    'task_tags',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
    Index('idx_task_tags_task_id', 'task_id'),
    Index('idx_task_tags_tag_id', 'tag_id')
)


class Contest(Base):
    """Model for Codeforces contests."""

    __tablename__ = 'contests'

    id = Column(Integer, primary_key=True)
    contest_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50))
    phase = Column(String(50))
    frozen = Column(Boolean, default=False)
    duration_seconds = Column(Integer)
    start_time_seconds = Column(Integer)
    relative_time_seconds = Column(Integer)

    # Relationships
    tasks = relationship('Task', back_populates='contest', cascade='all, delete-orphan')

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Contest contest_id={self.contest_id} name={self.name}>"


class Task(Base):
    """Model for Codeforces tasks/problems."""

    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    contest_id = Column(Integer, ForeignKey('contests.contest_id'), nullable=False, index=True)
    index = Column(String(10), nullable=False)
    name = Column(String(255), nullable=False)
    rating = Column(Integer, index=True)  # Difficulty rating (800, 900, ...)
    solved_count = Column(Integer, default=0, index=True)

    # Raw tags array from API
    tags = Column(ARRAY(String), default=[])

    # Time limits and memory limits
    time_limit = Column(Integer)
    memory_limit = Column(Integer)

    # Relationships
    contest = relationship('Contest', back_populates='tasks')
    tag_objects = relationship('Tag', secondary=task_tags, back_populates='tasks')

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_contest_index', 'contest_id', 'index', unique=True),
        Index('idx_rating_solved', 'rating', 'solved_count'),
    )

    @property
    def codeforces_url(self):
        """Generate Codeforces problem URL."""
        return f"https://codeforces.com/problemset/problem/{self.contest_id}/{self.index}"

    def __repr__(self):
        return f"<Task contest_id={self.contest_id} index={self.index} rating={self.rating}>"


class Tag(Base):
    """Model for problem tags/categories."""

    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False)

    # Relationships
    tasks = relationship('Task', secondary=task_tags, back_populates='tag_objects')

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Tag name={self.name}>"


class ParseHistory(Base):
    """Model for tracking parsing operations."""

    __tablename__ = 'parse_history'

    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime, default=datetime.utcnow, index=True)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(50), default='started')
    tasks_added = Column(Integer, default=0)
    tasks_updated = Column(Integer, default=0)
    contests_added = Column(Integer, default=0)
    tags_added = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<ParseHistory id={self.id} status={self.status}>"


class UserSettings(Base):
    """Model for user settings in Telegram bot."""

    __tablename__ = 'user_settings'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Default search preferences
    default_min_rating = Column(Integer, default=800)
    default_max_rating = Column(Integer, default=3500)
    preferred_tags = Column(ARRAY(String), default=[])

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserSettings telegram_id={self.telegram_id} username={self.username}>"


class SearchHistory(Base):
    """Model for tracking user search history."""

    __tablename__ = 'search_history'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user_settings.id', ondelete='CASCADE'), index=True)
    query = Column(String(255), nullable=True)
    min_rating = Column(Integer)
    max_rating = Column(Integer)
    tags = Column(ARRAY(String), default=[])
    results_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship('UserSettings')

    def __repr__(self):
        return f"<SearchHistory user_id={self.user_id} query={self.query}>"


def init_db(database_url):
    """Initialize database connection and create tables."""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
