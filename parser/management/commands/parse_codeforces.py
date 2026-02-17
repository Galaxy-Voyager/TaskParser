from django.core.management.base import BaseCommand
from parser.services.codeforces import CodeforcesParser


class Command(BaseCommand):
    help = 'Parse Codeforces problems and contests'

    def add_arguments(self, parser):
        parser.add_argument('--quiet', action='store_true', help='Suppress output')

    def handle(self, *args, **options):
        quiet = options.get('quiet', False)

        if not quiet:
            self.stdout.write("Starting Codeforces parser...")

        parser = CodeforcesParser()
        stats = parser.parse_and_save_all()

        if not quiet:
            self.stdout.write(self.style.SUCCESS(
                f"Done! Contests: {stats['contests_added']} (+{stats['contests_updated']} updated), "
                f"Tasks: {stats['tasks_added']} (+{stats['tasks_updated']} updated), "
                f"Tags: {stats['tags_added']}"
            ))
