from django.db import models

class College(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, unique=True)
    logo = models.ImageField(upload_to='college_logos/', blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
