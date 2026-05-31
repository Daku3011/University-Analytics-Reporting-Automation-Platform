from django.db import models
from colleges.models import College

class MonthlyAnalytics(models.Model):
    MONTH_CHOICES = [
        (1, 'January'), (2, 'February'), (3, 'March'),
        (4, 'April'), (5, 'May'), (6, 'June'),
        (7, 'July'), (8, 'August'), (9, 'September'),
        (10, 'October'), (11, 'November'), (12, 'December'),
    ]
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='analytics')
    month = models.IntegerField(choices=MONTH_CHOICES)
    year = models.IntegerField(default=2026)

    instagram_views = models.IntegerField(default=0)
    facebook_views = models.IntegerField(default=0)
    total_views = models.IntegerField(default=0)
    instagram_reach = models.IntegerField(default=0)
    facebook_reach = models.IntegerField(default=0)
    total_reach = models.IntegerField(default=0)
    instagram_followers = models.IntegerField(default=0)
    facebook_followers = models.IntegerField(default=0)
    youtube_subscribers = models.IntegerField(default=0)
    followers_gained = models.IntegerField(default=0)
    reels_count = models.IntegerField(default=0)
    graphics_count = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['college', 'month', 'year'], name='unique_monthly_analytics')
        ]
        indexes = [
            models.Index(fields=['year', 'month'], name='idx_analytics_year_month'),
        ]
        verbose_name_plural = 'Monthly Analytics'

    def __str__(self):
        return f"{self.college.code} - {self.get_month_display()} {self.year}"

class TopPost(models.Model):
    PLATFORM_CHOICES = [
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
    ]
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='top_posts')
    month = models.IntegerField(choices=MonthlyAnalytics.MONTH_CHOICES)
    year = models.IntegerField(default=2026)
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES)
    caption = models.TextField(blank=True)
    views = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    post_link = models.URLField(blank=True, verbose_name="Post Link")
    screenshot = models.ImageField(upload_to='top_posts/', blank=True, null=True)

    class Meta:
        ordering = ['-views']
        indexes = [
            models.Index(fields=['college', 'month', 'year', 'platform'], name='idx_toppost_lookup'),
            models.Index(fields=['year', 'month'], name='idx_toppost_year_month'),
        ]

    def __str__(self):
        return f"Top {self.platform} post - {self.views} views"