"""
Celery tasks for periodic parsing of Codeforces data.
"""

import os
import logging
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Initialize Celery app
app = Celery('taskparser')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3)
def parse_codeforces_tasks(self):
    """
    Celery task to parse Codeforces problems and contests.
    Runs every hour via Celery Beat.
    """
    from .codeforces_api import CodeforcesAPIClient, CodeforcesParser
    from .models import init_db

    logger.info("Starting Codeforces parsing task")

    try:
        # Get database URL from Django settings
        from django.conf import settings
        db_url = settings.DATABASE_URL

        # Initialize database session
        db_session = init_db(db_url)

        # Initialize API client
        api_client = CodeforcesAPIClient()

        # Initialize parser
        parser = CodeforcesParser(db_session, api_client)

        # Run parser
        stats = parser.parse_and_save_all()

        logger.info(f"Codeforces parsing completed successfully: {stats}")

        # Close session
        db_session.close()

        return stats

    except Exception as e:
        logger.error(f"Codeforces parsing failed: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
