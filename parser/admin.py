from django.contrib import admin
from django.db import models


# Note: This is for Django admin interface.
# SQLAlchemy models are managed separately.


class ParseHistoryAdmin(admin.ModelAdmin):
    """Admin interface for parse history."""
    list_display = ('id', 'start_time', 'end_time', 'status', 'tasks_added', 'tasks_updated')
    list_filter = ('status', 'start_time')
    search_fields = ('status',)
    readonly_fields = ('start_time', 'end_time', 'tasks_added', 'tasks_updated',
                       'contests_added', 'tags_added', 'error_message')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
