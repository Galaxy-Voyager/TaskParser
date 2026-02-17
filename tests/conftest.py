import pytest
from django.core.management import call_command
from parser.models import Tag

@pytest.fixture(autouse=True)
def clear_tags():
    """Clear tags before each test."""
    Tag.objects.all().delete()

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('migrate')
