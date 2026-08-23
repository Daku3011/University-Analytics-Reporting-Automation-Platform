from django.conf import settings
from django.db import models
from django.db.models import Q
from colleges.models import College, Department, Programme
import datetime
from su_analytics.constants import MONTH_CHOICES, PLATFORM_CHOICES

def get_current_year():
    return datetime.date.today().year

# Submission lifecycle for monthly analytics data (#2)
STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('submitted', 'Submitted'),
    ('incomplete', 'Incomplete'),
    ('verified', 'Verified'),
]

# Metrics that can have KPI targets assigned (#1)
ANALYSIS_METRIC_CHOICES = [
    ('instagram_views', 'Instagram Views'),
    ('facebook_views', 'Facebook Views'),
    ('total_views', 'Total Views'),
    ('instagram_reach', 'Instagram Reach'),
    ('facebook_reach', 'Facebook Reach'),
    ('total_reach', 'Total Reach'),
    ('instagram_followers', 'Instagram Followers'),
    ('facebook_followers', 'Facebook Followers'),
    ('youtube_subscribers', 'YouTube Subscribers'),
    ('followers_gained', 'Followers Gained'),
    ('reels_count', 'Reels Count'),
    ('graphics_count', 'Graphics Count'),
]

class MonthlyAnalytics(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='analytics')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, blank=True, null=True, related_name='analytics')
    programme = models.ForeignKey(Programme, on_delete=models.SET_NULL, blank=True, null=True, related_name='analytics')
    month = models.IntegerField(choices=MONTH_CHOICES)
    year = models.IntegerField(default=get_current_year)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True,
                              verbose_name="Submission Status")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
                                     related_name='submitted_analytics')
    submitted_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
                                    related_name='verified_analytics')
    verified_at = models.DateTimeField(blank=True, null=True)

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
            models.UniqueConstraint(
                fields=['college', 'month', 'year'], name='uq_college_monthly_analytics',
                condition=Q(department__isnull=True, programme__isnull=True)),
            models.UniqueConstraint(
                fields=['college', 'department', 'month', 'year'], name='uq_dept_monthly_analytics',
                condition=Q(department__isnull=False, programme__isnull=True)),
            models.UniqueConstraint(
                fields=['college', 'department', 'programme', 'month', 'year'], name='uq_prog_monthly_analytics',
                condition=Q(programme__isnull=False)),
        ]
        indexes = [
            models.Index(fields=['year', 'month'], name='idx_analytics_year_month'),
            models.Index(fields=['status'], name='idx_analytics_status'),
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


class KpiTarget(models.Model):
    """Consolidated KPI/target definition per college/department/programme (#1)."""
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='kpi_targets')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, blank=True, null=True, related_name='kpi_targets')
    programme = models.ForeignKey(Programme, on_delete=models.SET_NULL, blank=True, null=True, related_name='kpi_targets')
    year = models.IntegerField(default=get_current_year)
    metric = models.CharField(max_length=30, choices=ANALYSIS_METRIC_CHOICES)
    target_value = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['college', 'department', 'programme', 'year', 'metric'], name='uq_kpi_target')
        ]
        verbose_name_plural = 'KPI Targets'

    def __str__(self):
        scope = self.programme or self.department or self.college
        return f"KPI {self.get_metric_display()} {self.target_value} ({scope}, {self.year})"


class Alert(models.Model):
    """Automated alert for missing data, anomalies, or status gaps (#6)."""
    LEVEL_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]
    CATEGORY_CHOICES = [
        ('missing_data', 'Missing Data'),
        ('big_change', 'Big Change'),
        ('status', 'Submission Status'),
    ]
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='alerts')
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='info')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    month = models.IntegerField(choices=MONTH_CHOICES, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    # Stable identity for the scan engine (#6): rescans upsert on this key
    # instead of creating duplicates. Manual alerts (created via admin) keep
    # it null and are never auto-resolved.
    dedup_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    notified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Alerts'

    def __str__(self):
        return f"[{self.level}] {self.title}"