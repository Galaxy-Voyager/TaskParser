from django.contrib import admin
from .models import Contest, Tag, Task, ParseHistory


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ('contest_id', 'name', 'phase', 'start_time_seconds')
    list_filter = ('phase',)
    search_fields = ('name', 'contest_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('contest', 'index', 'name', 'rating', 'solved_count')
    list_filter = ('rating', 'tags')
    search_fields = ('name', 'contest__contest_id', 'index')
    filter_horizontal = ('tags',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ParseHistory)
class ParseHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'start_time', 'end_time', 'status', 'tasks_added')
    list_filter = ('status',)
    readonly_fields = ('start_time', 'end_time', 'tasks_added', 'tasks_updated',
                       'contests_added', 'tags_added', 'error_message')

    def has_add_permission(self, request):
        return False
