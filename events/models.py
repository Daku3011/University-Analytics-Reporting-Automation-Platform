from django.db import models
from colleges.models import College

class Event(models.Model):
    CATEGORY_CHOICES = [
        ('workshop', 'Workshop'),
        ('festival', 'Festival'),
        ('placement', 'Placement'),
        ('achievement', 'Achievement'),
        ('conference', 'Conference'),
        ('guest_lecture', 'Guest Lecture'),
        ('academic', 'Academic Event'),
        ('cultural', 'Cultural Event'),
        ('sports', 'Sports Event'),
        ('other', 'Other'),
    ]
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    date = models.DateField()
    is_carousel = models.BooleanField(default=False)
    is_reel = models.BooleanField(default=False)
    is_news = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['college', 'date'], name='idx_event_college_date'),
        ]

    def __str__(self):
        return f"{self.title} ({self.college.code})"

class Media(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('pdf', 'PDF'),
        ('reel', 'Reel'),
        ('poster', 'Poster'),
    ]
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='event_media/')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='image')

    def __str__(self):
        return f"{self.media_type} for {self.event.title[:50]}"
