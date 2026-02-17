from django.db import models


class Contest(models.Model):
    contest_id = models.IntegerField(unique=True, db_index=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, blank=True, null=True)
    phase = models.CharField(max_length=50, blank=True, null=True)
    frozen = models.BooleanField(default=False)
    duration_seconds = models.IntegerField(blank=True, null=True)
    start_time_seconds = models.IntegerField(blank=True, null=True)
    relative_time_seconds = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time_seconds']

    def __str__(self):
        return f"{self.contest_id}: {self.name}"


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Task(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='tasks')
    index = models.CharField(max_length=10)
    name = models.CharField(max_length=255)
    rating = models.IntegerField(blank=True, null=True, db_index=True)
    solved_count = models.IntegerField(default=0, db_index=True)
    tags = models.ManyToManyField(Tag, related_name='tasks', blank=True)
    tags_list = models.JSONField(default=list)  # для быстрого доступа без join
    time_limit = models.IntegerField(blank=True, null=True)
    memory_limit = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        unique_together = ['contest', 'index']
        ordering = ['-solved_count']
        indexes = [
            models.Index(fields=['rating', 'solved_count']),
        ]

    def __str__(self):
        return f"{self.contest.contest_id}{self.index}: {self.name}"

    @property
    def codeforces_url(self):
        return f"https://codeforces.com/problemset/problem/{self.contest.contest_id}/{self.index}"


class ParseHistory(models.Model):
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started')
    tasks_added = models.IntegerField(default=0)
    tasks_updated = models.IntegerField(default=0)
    contests_added = models.IntegerField(default=0)
    tags_added = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-start_time']
        verbose_name_plural = "Parse histories"

    def __str__(self):
        return f"Parse {self.id}: {self.status} at {self.start_time}"


class UserSettings(models.Model):
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    default_min_rating = models.IntegerField(default=800)
    default_max_rating = models.IntegerField(default=3500)
    preferred_tags = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Settings"
        verbose_name_plural = "User Settings"

    def __str__(self):
        return f"{self.telegram_id} - {self.username or self.first_name or 'Unknown'}"


class SearchHistory(models.Model):
    user = models.ForeignKey(UserSettings, on_delete=models.CASCADE, related_name='searches')
    query = models.CharField(max_length=255, blank=True, null=True)
    min_rating = models.IntegerField(blank=True, null=True)
    max_rating = models.IntegerField(blank=True, null=True)
    tags = models.JSONField(default=list)
    results_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Search History"
        verbose_name_plural = "Search Histories"
        ordering = ['-created_at']

    def __str__(self):
        return f"Search by {self.user} at {self.created_at}"
