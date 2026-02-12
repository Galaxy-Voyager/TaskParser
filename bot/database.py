"""
Database utilities for Telegram bot.
Provides functions to interact with SQLAlchemy models.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy import create_engine, and_, or_, desc, func
from sqlalchemy.orm import sessionmaker, Session

from django.conf import settings
from parser.models import Task, Tag, UserSettings, SearchHistory, init_db

logger = logging.getLogger(__name__)


class BotDatabase:
    """Database interface for Telegram bot."""

    def __init__(self):
        """Initialize database connection."""
        self.db_session = init_db(settings.DATABASE_URL)
        logger.info("Bot database initialized")

    def close(self):
        """Close database session."""
        self.db_session.close()

    def get_or_create_user(self, telegram_id: int, username: str = None,
                           first_name: str = None, last_name: str = None) -> UserSettings:
        """
        Get or create user settings.

        Args:
            telegram_id: Telegram user ID
            username: Telegram username
            first_name: User first name
            last_name: User last name

        Returns:
            UserSettings object
        """
        user = self.db_session.query(UserSettings).filter_by(
            telegram_id=telegram_id
        ).first()

        if not user:
            user = UserSettings(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            self.db_session.add(user)
            self.db_session.commit()
            logger.info(f"Created new user: {telegram_id}")
        else:
            # Update user info
            if username:
                user.username = username
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            user.updated_at = datetime.utcnow()
            self.db_session.commit()

        return user

    def get_all_tags(self) -> List[str]:
        """
        Get all unique tags from database.

        Returns:
            List of tag names sorted alphabetically
        """
        tags = self.db_session.query(Tag.name).order_by(Tag.name).all()
        return [tag[0] for tag in tags]

    def get_tasks_by_filters(self, min_rating: int = None, max_rating: int = None,
                             tags: List[str] = None, limit: int = 10) -> List[Task]:
        """
        Get tasks filtered by rating and tags.

        Args:
            min_rating: Minimum rating (default: 800)
            max_rating: Maximum rating (default: 3500)
            tags: List of tags to filter by
            limit: Maximum number of tasks to return

        Returns:
            List of Task objects
        """
        query = self.db_session.query(Task)

        # Filter by rating
        if min_rating:
            query = query.filter(Task.rating >= min_rating)
        if max_rating:
            query = query.filter(Task.rating <= max_rating)

        # Filter by tags
        if tags and len(tags) > 0:
            # Tasks that have all specified tags
            for tag in tags:
                query = query.filter(Task.tags.contains([tag]))

        # Order by solved_count (most solved first) and limit
        tasks = query.order_by(desc(Task.solved_count)).limit(limit).all()

        return tasks

    def search_tasks_by_query(self, query: str, limit: int = 10) -> List[Task]:
        """
        Search tasks by name or contest ID.

        Args:
            query: Search query (task name, contest ID, or index)
            limit: Maximum number of tasks to return

        Returns:
            List of Task objects
        """
        # Try to search by contest ID if query is numeric
        if query.isdigit():
            tasks = self.db_session.query(Task).filter(
                Task.contest_id == int(query)
            ).order_by(desc(Task.solved_count)).limit(limit).all()
            if tasks:
                return tasks

        # Search by task name (case insensitive)
        tasks = self.db_session.query(Task).filter(
            Task.name.ilike(f'%{query}%')
        ).order_by(desc(Task.solved_count)).limit(limit).all()

        return tasks

    def get_tasks_by_rating_range(self, min_rating: int, max_rating: int,
                                  limit: int = 10) -> List[Task]:
        """
        Get tasks within rating range, ordered by solved count.

        Args:
            min_rating: Minimum rating
            max_rating: Maximum rating
            limit: Maximum number of tasks

        Returns:
            List of Task objects
        """
        tasks = self.db_session.query(Task).filter(
            Task.rating >= min_rating,
            Task.rating <= max_rating
        ).order_by(desc(Task.solved_count)).limit(limit).all()

        return tasks

    def save_search_history(self, user_id: int, query: str = None,
                            min_rating: int = None, max_rating: int = None,
                            tags: List[str] = None, results_count: int = 0):
        """
        Save user search history.

        Args:
            user_id: UserSettings ID
            query: Search query (if any)
            min_rating: Minimum rating filter
            max_rating: Maximum rating filter
            tags: Tags filter
            results_count: Number of results found
        """
        history = SearchHistory(
            user_id=user_id,
            query=query,
            min_rating=min_rating,
            max_rating=max_rating,
            tags=tags or [],
            results_count=results_count
        )
        self.db_session.add(history)
        self.db_session.commit()

    def get_user_statistics(self, telegram_id: int) -> Dict[str, Any]:
        """
        Get user statistics.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Dictionary with user statistics
        """
        user = self.db_session.query(UserSettings).filter_by(
            telegram_id=telegram_id
        ).first()

        if not user:
            return {}

        # Get search history count
        search_count = self.db_session.query(SearchHistory).filter_by(
            user_id=user.id
        ).count()

        # Get favorite tags (most searched)
        favorite_tags = self.db_session.query(
            SearchHistory.tags, func.count(SearchHistory.tags)
        ).filter(
            SearchHistory.user_id == user.id
        ).group_by(SearchHistory.tags).order_by(
            desc(func.count(SearchHistory.tags))
        ).limit(5).all()

        return {
            'user': user,
            'search_count': search_count,
            'favorite_tags': [tag for tag, _ in favorite_tags if tag],
            'member_since': user.created_at
        }
