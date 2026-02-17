import pytest
from unittest.mock import patch, MagicMock
from parser.services.codeforces import CodeforcesAPIClient, CodeforcesParser

@pytest.mark.django_db
class TestCodeforcesAPIClient:
    def test_init(self):
        client = CodeforcesAPIClient()
        assert client.BASE_URL == "https://codeforces.com/api"
        assert client.min_interval == 2.0

    @patch('requests.Session.get')
    def test_get_problems_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'OK',
            'result': {
                'problems': [{'contestId': 1, 'index': 'A', 'name': 'Test'}],
                'problemStatistics': [{'contestId': 1, 'index': 'A', 'solvedCount': 100}]
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = CodeforcesAPIClient()
        problems = client.get_problems()
        assert len(problems) == 1
        assert problems[0]['solvedCount'] == 100
