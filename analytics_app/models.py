from django.db import models
from colleges.models import College
import datetime
from su_analytics.constants import MONTH_CHOICES, PLATFORM_CHOICES

def get_current_year():
    return datetime.date.today().year

class MonthlyAnalytics(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='analytics')
    month = models.IntegerField(choices=MONTH_CHOICES)
    year = models.IntegerField(default=get_current_year)

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

    def save(self, *args, **kwargs):
        self.total_views = self.instagram_views + self.facebook_views
        self.total_reach = self.instagram_reach + self.facebook_reach
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.college.code} - {self.get_month_display()} {self.year}"

class TopPost(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='top_posts')
    month = models.IntegerField(choices=MONTH_CHOICES)
    year = models.IntegerField(default=get_current_year)
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