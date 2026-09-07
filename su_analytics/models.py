from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class TaskTemplate(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    default_points = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Task(models.Model):

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    college = models.ForeignKey(
        'colleges.College', on_delete=models.CASCADE, related_name='tasks'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_tasks'
    )
    template = models.ForeignKey(
        TaskTemplate, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tasks'
    )
    points = models.IntegerField(default=10)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    due_date = models.DateField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.college})"

    def clean(self):
        """Enforce consistency between status and completed_at."""
        if self.completed_at and self.status != self.Status.COMPLETED:
            raise ValidationError(
                "completed_at can only be set when status is 'completed'."
            )
        if self.status == self.Status.COMPLETED and not self.completed_at:
            raise ValidationError(
                "completed_at is required when status is 'completed'."
            )

    def complete(self):
        """Atomically mark this task as completed."""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])


class AuditLog(models.Model):

    class Action(models.TextChoices):
        CREATE = 'CREATE', 'Create'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'
        LOGIN  = 'LOGIN',  'Login'
        LOGOUT = 'LOGOUT', 'Logout'
        EXPORT = 'EXPORT', 'Export'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    entity_type = models.CharField(max_length=100, db_index=True)
    # PositiveBigIntegerField matches Django's default BigAutoField PKs
    entity_id = models.PositiveBigIntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def save(self, *args, **kwargs):
        """AuditLog entries are immutable — updates are forbidden."""
        if self.pk:
            raise ValueError(
                "AuditLog entries cannot be modified after creation."
            )
        super().save(*args, **kwargs)

    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"{user_str} - {self.action} - {self.entity_type}"


class LoginSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='login_sessions'
    )
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['-login_time']

    def save(self, *args, **kwargs):
        """Keep is_active in sync with logout_time automatically."""
        if self.logout_time:
            self.is_active = False
        super().save(*args, **kwargs)

    @property
    def duration(self):
        """Returns timedelta of the session, or None if still active."""
        if self.logout_time:
            return self.logout_time - self.login_time
        return None

    def __str__(self):
        return f"{self.user.username} - {self.login_time}"
