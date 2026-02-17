import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests
from django.utils.text import slugify
from parser.models import Contest, Tag, Task, ParseHistory

logger = logging.getLogger(__name__)


class CodeforcesAPIError(Exception):
    pass


class CodeforcesAPIClient:
    BASE_URL = "https://codeforces.com/api"

    def __init__(self):
        self.session = requests.Session()
        self.last_request_time = 0
        self.min_interval = 2.0

    def _wait_for_rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_interval:
            time.sleep(self.min_interval - time_since_last)
        self.last_request_time = time.time()

    def get_problems(self) -> List[Dict[str, Any]]:
        self._wait_for_rate_limit()
        response = self.session.get(f"{self.BASE_URL}/problemset.problems", timeout=30)
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'FAILED':
            raise CodeforcesAPIError(data.get('comment', 'Unknown API error'))

        problems = data['result'].get('problems', [])
        stats_map = {
            (s['contestId'], s['index']): s['solvedCount']
            for s in data['result'].get('problemStatistics', [])
        }

        for problem in problems:
            key = (problem.get('contestId'), problem.get('index'))
            problem['solvedCount'] = stats_map.get(key, 0)

        return problems

    def get_contests(self) -> List[Dict[str, Any]]:
        self._wait_for_rate_limit()
        response = self.session.get(f"{self.BASE_URL}/contest.list", timeout=30)
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'FAILED':
            raise CodeforcesAPIError(data.get('comment', 'Unknown API error'))

        return data['result']


class CodeforcesParser:
    def __init__(self):
        self.api_client = CodeforcesAPIClient()

    def parse_and_save_all(self) -> Dict[str, int]:
        history = ParseHistory.objects.create(status='started')
        stats = {
            'contests_added': 0,
            'contests_updated': 0,
            'tasks_added': 0,
            'tasks_updated': 0,
            'tags_added': 0,
        }

        try:
            # Загружаем данные
            contests_data = self.api_client.get_contests()
            problems_data = self.api_client.get_problems()

            # Сохраняем контесты
            contest_map = {}
            for contest_data in contests_data:
                contest_id = contest_data['id']
                contest, created = Contest.objects.update_or_create(
                    contest_id=contest_id,
                    defaults={
                        'name': contest_data.get('name', ''),
                        'type': contest_data.get('type'),
                        'phase': contest_data.get('phase'),
                        'frozen': contest_data.get('frozen', False),
                        'duration_seconds': contest_data.get('durationSeconds'),
                        'start_time_seconds': contest_data.get('startTimeSeconds'),
                        'relative_time_seconds': contest_data.get('relativeTimeSeconds'),
                    }
                )
                contest_map[contest_id] = contest
                if created:
                    stats['contests_added'] += 1
                else:
                    stats['contests_updated'] += 1

            # Сохраняем теги
            all_tags = set()
            for problem in problems_data:
                all_tags.update(problem.get('tags', []))

            tag_map = {}
            for tag_name in all_tags:
                tag, created = Tag.objects.get_or_create(
                    name=tag_name,
                    defaults={'slug': slugify(tag_name)}
                )
                tag_map[tag_name] = tag
                if created:
                    stats['tags_added'] += 1

            # Сохраняем задачи
            for problem in problems_data:
                contest_id = problem.get('contestId')
                index = problem.get('index')

                if not contest_id or not index:
                    continue

                contest = contest_map.get(contest_id)
                if not contest:
                    continue

                task, created = Task.objects.update_or_create(
                    contest=contest,
                    index=index,
                    defaults={
                        'name': problem.get('name', ''),
                        'rating': problem.get('rating'),
                        'solved_count': problem.get('solvedCount', 0),
                        'tags_list': problem.get('tags', []),
                        'time_limit': problem.get('timeLimit'),
                        'memory_limit': problem.get('memoryLimit'),
                    }
                )

                # Добавляем связи с тегами
                if created or task.tags.exists() != bool(problem.get('tags')):
                    task.tags.set([tag_map[t] for t in problem.get('tags', []) if t in tag_map])

                if created:
                    stats['tasks_added'] += 1
                else:
                    stats['tasks_updated'] += 1

            # Обновляем историю
            history.status = 'success'
            history.end_time = datetime.now()
            history.tasks_added = stats['tasks_added']
            history.tasks_updated = stats['tasks_updated']
            history.contests_added = stats['contests_added']
            history.tags_added = stats['tags_added']
            history.save()

            logger.info(f"Parse completed: {stats}")

        except Exception as e:
            history.status = 'failed'
            history.end_time = datetime.now()
            history.error_message = str(e)
            history.save()
            logger.error(f"Parse failed: {e}")
            raise

        return stats
