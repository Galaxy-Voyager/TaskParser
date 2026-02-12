"""
Tests for Codeforces API client and parser.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ИМПОРТИРУЕМ ФИКСТУРУ ИЗ CONFTEST
from tests.conftest import db_session, engine

from parser.codeforces_api import CodeforcesAPIClient, CodeforcesParser, CodeforcesAPIError
from parser.models import Base, Contest, Task, Tag, ParseHistory


class TestCodeforcesAPIClient:
    """Test Codeforces API client."""

    def test_init(self):
        """Test client initialization."""
        client = CodeforcesAPIClient()
        assert client.BASE_URL == "https://codeforces.com/api"
        assert client.min_interval == 2.0

        client = CodeforcesAPIClient(api_key="test_key", api_secret="test_secret")
        assert client.api_key == "test_key"
        assert client.api_secret == "test_secret"

    @patch('parser.codeforces_api.requests.Session')
    def test_get_problems_success(self, mock_session):
        """Test successful problems fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "result": {
                "problems": [
                    {
                        "contestId": 1,
                        "index": "A",
                        "name": "Test Problem",
                        "rating": 800,
                        "tags": ["math", "implementation"]
                    }
                ],
                "problemStatistics": [
                    {
                        "contestId": 1,
                        "index": "A",
                        "solvedCount": 1000
                    }
                ]
            }
        }
        mock_response.raise_for_status.return_value = None

        mock_session.return_value.get.return_value = mock_response

        client = CodeforcesAPIClient()
        problems = client.get_problems()

        assert len(problems) == 1
        assert problems[0]["contestId"] == 1
        assert problems[0]["index"] == "A"
        assert problems[0]["solvedCount"] == 1000

    @patch('parser.codeforces_api.requests.Session')
    def test_get_problems_failed(self, mock_session):
        """Test failed problems fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "FAILED",
            "comment": "API limit exceeded"
        }
        mock_response.raise_for_status.return_value = None

        mock_session.return_value.get.return_value = mock_response

        client = CodeforcesAPIClient()

        with pytest.raises(CodeforcesAPIError) as excinfo:
            client.get_problems()

        assert "API limit exceeded" in str(excinfo.value)

    @patch('parser.codeforces_api.requests.Session')
    def test_get_contests_success(self, mock_session):
        """Test successful contests fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "result": [
                {
                    "id": 1,
                    "name": "Test Contest",
                    "type": "CF",
                    "phase": "FINISHED",
                    "durationSeconds": 7200,
                    "startTimeSeconds": 1600000000
                }
            ]
        }
        mock_response.raise_for_status.return_value = None

        mock_session.return_value.get.return_value = mock_response

        client = CodeforcesAPIClient()
        contests = client.get_contests()

        assert len(contests) == 1
        assert contests[0]["id"] == 1
        assert contests[0]["name"] == "Test Contest"

    @patch('parser.codeforces_api.requests.Session')
    def test_http_error(self, mock_session):
        """Test HTTP error handling."""
        from requests.exceptions import RequestException

        mock_session.return_value.get.side_effect = RequestException("Connection error")

        client = CodeforcesAPIClient()

        with pytest.raises(CodeforcesAPIError) as excinfo:
            client.get_problems()

        assert "HTTP request failed" in str(excinfo.value)

    def test_rate_limiting(self):
        """Test rate limiting between requests."""
        import time

        client = CodeforcesAPIClient()
        client.min_interval = 0.1  # Set to 0.1 seconds for test

        start = time.time()
        client._wait_for_rate_limit()
        client._wait_for_rate_limit()
        end = time.time()

        assert end - start >= 0.1


class TestCodeforcesParser:
    """Test Codeforces parser."""

    # УДАЛЯЕМ SQLite фикстуру - используем общую из conftest.py
    # @pytest.fixture
    # def db_session(self):
    #     """Create database session for parser tests using SQLite in memory."""
    #     engine = create_engine('sqlite:///:memory:')
    #     Base.metadata.create_all(engine)
    #     Session = sessionmaker(bind=engine)
    #     session = Session()
    #     yield session
    #     session.close()

    @pytest.fixture
    def mock_api_client(self):
        """Create mock API client."""
        client = Mock(spec=CodeforcesAPIClient)
        client.get_contests.return_value = [
            {
                'id': 1,
                'name': 'Contest 1',
                'type': 'CF',
                'phase': 'FINISHED',
                'durationSeconds': 7200,
                'startTimeSeconds': 1600000000
            }
        ]
        client.get_problems.return_value = [
            {
                'contestId': 1,
                'index': 'A',
                'name': 'Problem A',
                'rating': 800,
                'solvedCount': 100,
                'tags': ['math', 'implementation'],
                'timeLimit': 1000,
                'memoryLimit': 256
            },
            {
                'contestId': 1,
                'index': 'B',
                'name': 'Problem B',
                'rating': 1200,
                'solvedCount': 50,
                'tags': ['dp', 'greedy'],
                'timeLimit': 2000,
                'memoryLimit': 512
            }
        ]
        return client

    def test_parse_and_save_all_new(self, db_session, mock_api_client):
        """Test full parsing flow with new data."""
        parser = CodeforcesParser(db_session, mock_api_client)
        stats = parser.parse_and_save_all()

        # Check stats
        assert stats['contests_added'] == 1
        assert stats['contests_updated'] == 0
        assert stats['tasks_added'] == 2
        assert stats['tasks_updated'] == 0
        assert stats['tags_added'] == 4  # math, implementation, dp, greedy

        # Check contest
        contest = db_session.query(Contest).filter_by(contest_id=1).first()
        assert contest is not None
        assert contest.name == 'Contest 1'

        # Check tasks
        tasks = db_session.query(Task).filter_by(contest_id=1).all()
        assert len(tasks) == 2

        task_a = db_session.query(Task).filter_by(contest_id=1, index='A').first()
        assert task_a is not None
        assert task_a.name == 'Problem A'
        assert task_a.rating == 800
        assert task_a.solved_count == 100
        assert task_a.tags == ['math', 'implementation']

        # Check tags
        tags = db_session.query(Tag).all()
        assert len(tags) == 4
        tag_names = [tag.name for tag in tags]
        assert 'math' in tag_names
        assert 'implementation' in tag_names
        assert 'dp' in tag_names
        assert 'greedy' in tag_names

        # Check parse history
        history = db_session.query(ParseHistory).first()
        assert history is not None
        assert history.status == 'success'
        assert history.tasks_added == 2
        assert history.tags_added == 4

    def test_parse_and_save_all_update(self, db_session, mock_api_client):
        """Test parsing flow with existing data update."""
        # First parse
        parser = CodeforcesParser(db_session, mock_api_client)
        parser.parse_and_save_all()

        # Update mock data - теперь только тег 'math'
        mock_api_client.get_problems.return_value = [
            {
                'contestId': 1,
                'index': 'A',
                'name': 'Problem A Updated',
                'rating': 900,
                'solvedCount': 200,
                'tags': ['math'],  # Только один тег
                'timeLimit': 1000,
                'memoryLimit': 256
            }
        ]

        # Second parse
        stats = parser.parse_and_save_all()

        assert stats['contests_added'] == 0
        assert stats['contests_updated'] == 1
        assert stats['tasks_added'] == 0
        assert stats['tasks_updated'] == 1
        assert stats['tags_added'] == 0

        # Check updated task
        task = db_session.query(Task).filter_by(contest_id=1, index='A').first()
        assert task.name == 'Problem A Updated'
        assert task.rating == 900
        assert task.solved_count == 200

        # Проверяем что теги обновились (старые удалились, новый добавился)
        assert task.tags == ['math']  # Теперь должно работать


    def test_parse_without_rating(self, db_session):
        """Test parsing tasks without rating."""
        mock_client = Mock(spec=CodeforcesAPIClient)
        mock_client.get_contests.return_value = [{'id': 1, 'name': 'Contest 1'}]
        mock_client.get_problems.return_value = [
            {
                'contestId': 1,
                'index': 'A',
                'name': 'No Rating Problem',
                'solvedCount': 10,
                'tags': []
            }
        ]

        parser = CodeforcesParser(db_session, mock_client)
        stats = parser.parse_and_save_all()

        assert stats['tasks_added'] == 1

        task = db_session.query(Task).filter_by(contest_id=1, index='A').first()
        assert task.rating is None
        assert task.solved_count == 10

    def test_parse_error_handling(self, db_session, mock_api_client):
        """Test error handling during parsing."""
        mock_api_client.get_problems.side_effect = CodeforcesAPIError("Network error")

        parser = CodeforcesParser(db_session, mock_api_client)

        with pytest.raises(CodeforcesAPIError):
            parser.parse_and_save_all()

        # Check that error was logged in history
        history = db_session.query(ParseHistory).first()
        assert history is not None
        assert history.status == 'failed'
        assert 'Network error' in history.error_message

    def test_contest_not_found(self, db_session):
        """Test handling of contest not found for task."""
        mock_client = Mock(spec=CodeforcesAPIClient)
        mock_client.get_contests.return_value = []
        mock_client.get_problems.return_value = [
            {
                'contestId': 999,
                'index': 'A',
                'name': 'Orphan Problem',
                'rating': 800,
                'solvedCount': 10,
                'tags': ['math']
            }
        ]

        parser = CodeforcesParser(db_session, mock_client)
        stats = parser.parse_and_save_all()

        assert stats['tasks_added'] == 0  # Task not added because contest not found
        assert stats['contests_added'] == 0

    def test_slugify(self, db_session):
        """Test tag slug generation."""
        parser = CodeforcesParser(db_session, Mock())
        assert parser._slugify("Two Pointers") == "two-pointers"
        assert parser._slugify("Dynamic Programming") == "dynamic-programming"
        assert parser._slugify("C++") == "c"
        assert parser._slugify("2-sat") == "2-sat"
        assert parser._slugify("  spaces  ") == "spaces"
