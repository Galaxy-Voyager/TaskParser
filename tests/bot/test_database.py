import pytest
import asyncio
from asgiref.sync import sync_to_async
from bot.database import BotDatabase
from parser.models import UserSettings, Tag, Task, Contest, SearchHistory
from django.db import transaction


@pytest.fixture
def db():
    """Create BotDatabase instance."""
    return BotDatabase()


@pytest.fixture
def contest():
    """Create test contest."""
    return Contest.objects.create(
        contest_id=1,
        name='Test Contest',
        type='CF',
        phase='FINISHED'
    )


@pytest.mark.django_db(transaction=True)
class TestBotDatabase:
    @pytest.mark.asyncio
    async def test_get_or_create_user(self, db):
        user = await db.get_or_create_user(
            telegram_id=12345,
            username='test_user',
            first_name='Test',
            last_name='User'
        )
        assert user.telegram_id == 12345
        assert user.username == 'test_user'
        assert user.first_name == 'Test'
        assert user.last_name == 'User'

    def test_get_all_tags_sync(self, db):
        with transaction.atomic():
            Tag.objects.all().delete()
            Tag.objects.create(name='math', slug='math')
            Tag.objects.create(name='dp', slug='dp')

        tag_list = asyncio.run(db.get_all_tags())
        assert 'math' in tag_list
        assert 'dp' in tag_list
        assert len(tag_list) == 2

    @pytest.mark.asyncio
    async def test_get_tasks_by_filters(self, db, contest):
        await sync_to_async(Task.objects.all().delete)()

        await sync_to_async(Task.objects.create)(
            contest=contest,
            index='A',
            name='Easy Problem',
            rating=800,
            solved_count=1000,
            tags_list=['math']
        )
        await sync_to_async(Task.objects.create)(
            contest=contest,
            index='B',
            name='Dynamic Problem',
            rating=1500,
            solved_count=500,
            tags_list=['dp']
        )

        # Фильтр по рейтингу
        tasks = await db.get_tasks_by_filters(
            min_rating=800,
            max_rating=1200,
            limit=10
        )
        assert len(tasks) == 1
        assert tasks[0].index == 'A'

        # Фильтр по тегам
        tasks = await db.get_tasks_by_filters(
            tags=['math'],
            limit=10
        )
        assert len(tasks) == 1
        assert tasks[0].index == 'A'

    @pytest.mark.asyncio
    async def test_search_tasks_by_query(self, db, contest):
        await sync_to_async(Task.objects.all().delete)()

        await sync_to_async(Task.objects.create)(
            contest=contest,
            index='A',
            name='Easy Problem',
            solved_count=1000
        )

        tasks = await db.search_tasks_by_query('Easy')
        assert len(tasks) == 1
        assert tasks[0].name == 'Easy Problem'

    @pytest.mark.asyncio
    async def test_save_search_history(self, db):
        user = await db.get_or_create_user(telegram_id=12345)

        await db.save_search_history(
            user_id=user.id,
            query='test',
            min_rating=800,
            max_rating=1200,
            tags=['math'],
            results_count=5
        )

        @sync_to_async
        def get_history():
            return SearchHistory.objects.filter(user_id=user.id).first()

        history = await get_history()
        assert history is not None
        assert history.query == 'test'
        assert history.min_rating == 800
        assert history.max_rating == 1200
        assert history.tags == ['math']
        assert history.results_count == 5

    @pytest.mark.asyncio
    async def test_get_user_statistics(self, db):
        user = await db.get_or_create_user(telegram_id=12345)

        await sync_to_async(SearchHistory.objects.filter(user_id=user.id).delete)()

        for i in range(3):
            await db.save_search_history(
                user_id=user.id,
                query=f'test{i}',
                results_count=5
            )

        stats = await db.get_user_statistics(12345)
        assert stats['user'].id == user.id
        assert stats['search_count'] == 3
        assert 'member_since' in stats
