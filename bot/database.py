import logging
from asgiref.sync import sync_to_async
from django.db.models import Q
from parser.models import Task, Tag, UserSettings, SearchHistory

logger = logging.getLogger(__name__)


class BotDatabase:
    @sync_to_async
    def get_or_create_user(self, telegram_id, username=None, first_name=None, last_name=None):
        user, created = UserSettings.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
            }
        )
        if not created:
            user.username = username or user.username
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            user.save()
        return user

    @sync_to_async
    def get_all_tags(self):
        return list(Tag.objects.values_list('name', flat=True).order_by('name'))

    @sync_to_async
    def get_tasks_by_filters(self, min_rating=None, max_rating=None, tags=None, limit=10):
        queryset = Task.objects.all()

        if min_rating:
            queryset = queryset.filter(rating__gte=min_rating)
        if max_rating:
            queryset = queryset.filter(rating__lte=max_rating)
        if tags:
            for tag in tags:
                queryset = queryset.filter(tags_list__contains=[tag])

        return list(queryset.order_by('-solved_count')[:limit])

    @sync_to_async
    def search_tasks_by_query(self, query, limit=10):
        if query.isdigit():
            tasks = Task.objects.filter(contest__contest_id=int(query))
            if tasks.exists():
                return list(tasks.order_by('-solved_count')[:limit])

        return list(Task.objects.filter(
            Q(name__icontains=query)
        ).order_by('-solved_count')[:limit])

    @sync_to_async
    def save_search_history(self, user_id, query=None, min_rating=None, max_rating=None, tags=None, results_count=0):
        SearchHistory.objects.create(
            user_id=user_id,
            query=query,
            min_rating=min_rating,
            max_rating=max_rating,
            tags=tags or [],
            results_count=results_count
        )

    @sync_to_async
    def get_user_statistics(self, telegram_id):
        try:
            user = UserSettings.objects.get(telegram_id=telegram_id)
        except UserSettings.DoesNotExist:
            return {}

        search_count = SearchHistory.objects.filter(user_id=user.id).count()

        return {
            'user': user,
            'search_count': search_count,
            'favorite_tags': [],
            'member_since': user.created_at
        }
