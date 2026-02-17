from celery import shared_task
import logging
from parser.services.codeforces import CodeforcesParser

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def parse_codeforces_tasks(self):
    logger.info("Starting Codeforces parsing task")
    try:
        parser = CodeforcesParser()
        stats = parser.parse_and_save_all()
        logger.info(f"Parse completed: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Parse failed: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
