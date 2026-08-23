from django.db import models


class University(models.Model):
    """Top-level institution. Typically a single instance (e.g. Sarvajanik University)."""
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, unique=True, blank=True)
    short_name = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Universities'

    def __str__(self):
        return self.short_name or self.name


class College(models.Model):
    university = models.ForeignKey(
        University, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='colleges', verbose_name='University',
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, unique=True)
    logo = models.ImageField(upload_to='college_logos/', blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Department(models.Model):
    """Academic department within a college/institute."""
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['college', 'name'], name='unique_department_per_college'),
        ]

    def __str__(self):
        return f"{self.college.code} / {self.name}"


class Programme(models.Model):
    """Academic programme/course within a department."""
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='programmes')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['department', 'name'], name='unique_programme_per_department'),
        ]

    def __str__(self):
        return f"{self.department.name} / {self.name}"
