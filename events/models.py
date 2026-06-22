from django.db import models
from colleges.models import College
from su_analytics.constants import EVENT_CATEGORY_CHOICES, MEDIA_TYPE_CHOICES

class Event(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=EVENT_CATEGORY_CHOICES, default='other')
    date = models.DateField()
    is_carousel = models.BooleanField(default=False)
    is_reel = models.BooleanField(default=False)
    is_news = models.BooleanField(default=False)
    social_media_link = models.URLField(blank=True, verbose_name="Social Media Account Link")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['college', 'date'], name='idx_event_college_date'),
        ]

    def __str__(self):
        return f"{self.title} ({self.college.code})"

class Media(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='event_media/')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='image')

    def __str__(self):
        return f"{self.media_type} for {self.event.title[:50]}"
