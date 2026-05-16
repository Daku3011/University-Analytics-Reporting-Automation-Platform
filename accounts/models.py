from django.db import models
from django.contrib.auth.models import User
from colleges.models import College

class Profile(models.Model):
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('college_admin', 'College Admin'),
        ('analytics_team', 'Analytics Team'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='college_admin')
    college = models.ForeignKey(College, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
