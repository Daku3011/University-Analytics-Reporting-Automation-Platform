from django.db import models
from django.conf import settings
from colleges.models import College
from su_analytics.constants import EVENT_CATEGORY_CHOICES, MEDIA_TYPE_CHOICES


class Event(models.Model):

    class ApprovalStatus(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        REJECTED  = 'rejected',  'Rejected'

    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=EVENT_CATEGORY_CHOICES, default='other')
    date = models.DateField()
    is_carousel = models.BooleanField(default=False)
    is_reel = models.BooleanField(default=False)
    is_news = models.BooleanField(default=False)
    social_media_link = models.URLField(blank=True, verbose_name="Social Media Account Link")

    # ── Approval workflow ────────────────────────────────────────────
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_events',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_events',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['college', 'date'], name='idx_event_college_date'),
            models.Index(fields=['approval_status'], name='idx_event_approval_status'),
        ]

    def __str__(self):
        return f"{self.title} ({self.college.code})"

    # ── Convenience helpers ──────────────────────────────────────────
    @property
    def is_pending(self):
        return self.approval_status == self.ApprovalStatus.PENDING

    @property
    def is_confirmed(self):
        return self.approval_status == self.ApprovalStatus.CONFIRMED

    @property
    def is_rejected(self):
        return self.approval_status == self.ApprovalStatus.REJECTED

    def confirm(self, reviewed_by):
        """Mark event as confirmed by a super admin."""
        from django.utils import timezone
        self.approval_status = self.ApprovalStatus.CONFIRMED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.rejection_reason = ''
        self.save(update_fields=['approval_status', 'reviewed_by', 'reviewed_at', 'rejection_reason'])

    def reject(self, reviewed_by, reason=''):
        """Mark event as rejected with an optional reason."""
        from django.utils import timezone
        self.approval_status = self.ApprovalStatus.REJECTED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save(update_fields=['approval_status', 'reviewed_by', 'reviewed_at', 'rejection_reason'])


class Media(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='event_media/')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='image')

    def __str__(self):
        return f"{self.media_type} for {self.event.title[:50]}"
