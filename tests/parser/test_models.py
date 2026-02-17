import pytest
from parser.models import Contest, Tag, Task, ParseHistory

@pytest.fixture
def contest():
    return Contest.objects.create(
        contest_id=1,
        name='Test Contest',
        type='CF',
        phase='FINISHED'
    )

@pytest.mark.django_db
class TestContestModel:
    def test_create_contest(self):
        contest = Contest.objects.create(
            contest_id=1,
            name='Test Contest'
        )
        assert contest.contest_id == 1
        assert contest.name == 'Test Contest'
        assert str(contest) == '1: Test Contest'

@pytest.mark.django_db
class TestTagModel:
    def test_create_tag(self):
        tag = Tag.objects.create(
            name='math',
            slug='math'
        )
        assert tag.name == 'math'
        assert tag.slug == 'math'
        assert str(tag) == 'math'

@pytest.mark.django_db
class TestTaskModel:
    def test_create_task(self, contest):
        task = Task.objects.create(
            contest=contest,
            index='A',
            name='Test Problem',
            rating=800,
            solved_count=1000,
            tags_list=['math', 'implementation']
        )
        assert task.contest.contest_id == 1
        assert task.index == 'A'
        assert task.name == 'Test Problem'
        assert task.rating == 800
        assert task.solved_count == 1000
        assert task.tags_list == ['math', 'implementation']
        assert task.codeforces_url == 'https://codeforces.com/problemset/problem/1/A'
