"""
Codeforces API client for fetching problems and contests data.
"""

import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from parser.models import Contest

logger = logging.getLogger(__name__)


class CodeforcesAPIError(Exception):
    """Custom exception for Codeforces API errors."""
    pass


class CodeforcesAPIClient:
    """
    Client for Codeforces API.
    API documentation: https://codeforces.com/apiHelp
    Rate limit: 1 request per 2 seconds
    """

    BASE_URL = "https://codeforces.com/api"

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = self._create_session()
        self.last_request_time = 0
        self.min_interval = 2.0

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _wait_for_rate_limit(self):
        """Ensure we don't exceed API rate limit."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _make_request(self, method_name: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make request to Codeforces API.

        Args:
            method_name: API method name
            params: Request parameters

        Returns:
            API response as dictionary

        Raises:
            CodeforcesAPIError: If API request fails
        """
        self._wait_for_rate_limit()

        url = f"{self.BASE_URL}/{method_name}"
        params = params or {}

        try:
            logger.debug(f"Making request to {url}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if data['status'] == 'FAILED':
                error_msg = data.get('comment', 'Unknown API error')
                raise CodeforcesAPIError(f"API request failed: {error_msg}")

            return data['result']

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            raise CodeforcesAPIError(f"HTTP request failed: {e}")
        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise CodeforcesAPIError(f"Invalid JSON response: {e}")

    def get_problems(self) -> List[Dict[str, Any]]:
        """
        Fetch all problems from Codeforces.

        Returns:
            List of problems with their details
        """
        result = self._make_request("problemset.problems")

        problems = result.get('problems', [])

        # Combine problem data with statistics
        for problem in problems:
            contest_id = problem.get('contestId')
            index = problem.get('index')

            # Find matching statistics
            for stat in result.get('problemStatistics', []):
                if stat.get('contestId') == contest_id and stat.get('index') == index:
                    problem['solvedCount'] = stat.get('solvedCount', 0)
                    break
            else:
                problem['solvedCount'] = 0

        logger.info(f"Fetched {len(problems)} problems from Codeforces")
        return problems

    def get_contests(self) -> List[Dict[str, Any]]:
        """
        Fetch all contests from Codeforces.

        Returns:
            List of contests
        """
        result = self._make_request("contest.list")
        logger.info(f"Fetched {len(result)} contests from Codeforces")
        return result


class CodeforcesParser:
    """
    Parser for Codeforces problems and contests.
    Handles data transformation and storage.
    """

    def __init__(self, db_session, api_client: Optional[CodeforcesAPIClient] = None):
        self.db_session = db_session
        self.api_client = api_client or CodeforcesAPIClient()
        self.logger = logging.getLogger(__name__)

    def parse_and_save_all(self) -> Dict[str, int]:
        """
        Parse all problems and contests and save to database.

        Returns:
            Dictionary with counts of added/updated items
        """
        from .models import Contest, Task, Tag, ParseHistory

        history = ParseHistory(start_time=datetime.utcnow(), status='started')
        self.db_session.add(history)
        self.db_session.commit()

        stats = {
            'contests_added': 0,
            'contests_updated': 0,
            'tasks_added': 0,
            'tasks_updated': 0,
            'tags_added': 0,
        }

        try:
            # Fetch contests and problems
            contests_data = self.api_client.get_contests()
            problems_data = self.api_client.get_problems()

            # Process contests
            contest_map = self._process_contests(contests_data, stats)

            # Process problems
            self._process_problems(problems_data, contest_map, stats)

            # Update history
            history.status = 'success'
            history.end_time = datetime.utcnow()
            history.contests_added = stats['contests_added']
            history.tasks_added = stats['tasks_added']
            history.tags_added = stats['tags_added']

            self.db_session.commit()
            self.logger.info(f"Parse completed successfully. Stats: {stats}")

        except Exception as e:
            self.logger.error(f"Parse failed: {e}")
            history.status = 'failed'
            history.end_time = datetime.utcnow()
            history.error_message = str(e)
            self.db_session.commit()
            raise

        return stats

    def _process_contests(self, contests_data: List[Dict], stats: Dict) -> Dict[int, Contest]:
        """Process and save contests to database."""
        from .models import Contest

        contest_map = {}

        for contest_data in contests_data:
            contest_id = contest_data.get('id')

            # Отключаем автофлеш для этой операции
            with self.db_session.no_autoflush:
                contest = self.db_session.query(Contest).filter_by(contest_id=contest_id).first()

                if contest:
                    # Update existing contest
                    contest.phase = contest_data.get('phase', contest.phase)
                    contest.name = contest_data.get('name', contest.name)
                    stats['contests_updated'] += 1
                else:
                    # Create new contest
                    contest = Contest(
                        contest_id=contest_id,
                        name=contest_data.get('name', ''),
                        type=contest_data.get('type'),
                        phase=contest_data.get('phase'),
                        frozen=contest_data.get('frozen', False),
                        duration_seconds=contest_data.get('durationSeconds'),
                        start_time_seconds=contest_data.get('startTimeSeconds'),
                        relative_time_seconds=contest_data.get('relativeTimeSeconds'),
                    )
                    self.db_session.add(contest)
                    stats['contests_added'] += 1

                contest_map[contest_id] = contest

        self.db_session.flush()
        return contest_map

    def _process_problems(self, problems_data: List[Dict], contest_map: Dict[int, Contest], stats: Dict):
        """Process and save problems to database."""
        from .models import Task, Tag

        # Get or create tags
        all_tags = set()
        for problem in problems_data:
            all_tags.update(problem.get('tags', []))

        tag_objects = {}
        for tag_name in all_tags:
            tag = self.db_session.query(Tag).filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(
                    name=tag_name,
                    slug=self._slugify(tag_name)
                )
                self.db_session.add(tag)
                stats['tags_added'] += 1
            tag_objects[tag_name] = tag

        self.db_session.flush()

        # Process each problem
        for problem_data in problems_data:
            contest_id = problem_data.get('contestId')
            index = problem_data.get('index')

            if not contest_id or not index:
                continue

            task = self.db_session.query(Task).filter_by(
                contest_id=contest_id,
                index=index
            ).first()

            if task:
                # Update existing task
                task.name = problem_data.get('name', task.name)
                task.rating = problem_data.get('rating', task.rating)
                task.solved_count = problem_data.get('solvedCount', task.solved_count)
                task.tags = problem_data.get('tags', [])

                # Очищаем связи с тегами
                task.tag_objects = []

                stats['tasks_updated'] += 1
            else:
                # Create new task
                contest = contest_map.get(contest_id)
                if not contest:
                    continue

                task = Task(
                    contest_id=contest_id,
                    index=index,
                    name=problem_data.get('name', ''),
                    rating=problem_data.get('rating'),
                    solved_count=problem_data.get('solvedCount', 0),
                    time_limit=problem_data.get('timeLimit'),
                    memory_limit=problem_data.get('memoryLimit'),
                    tags=problem_data.get('tags', []),  # Добавляем теги сразу
                    contest=contest
                )
                self.db_session.add(task)
                stats['tasks_added'] += 1

            # Добавляем новые теги
            for tag_name in problem_data.get('tags', []):
                tag = tag_objects.get(tag_name)
                if tag and tag not in task.tag_objects:
                    task.tag_objects.append(tag)

        self.db_session.flush()

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')
