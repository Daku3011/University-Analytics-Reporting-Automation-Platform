from django.db import models
from colleges.models import College

class MonthlyReport(models.Model):
    MONTH_CHOICES = [
        (1, 'January'), (2, 'February'), (3, 'March'),
        (4, 'April'), (5, 'May'), (6, 'June'),
        (7, 'July'), (8, 'August'), (9, 'September'),
        (10, 'October'), (11, 'November'), (12, 'December'),
    ]
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='monthly_reports')
    month = models.IntegerField(choices=MONTH_CHOICES)
    year = models.IntegerField(default=2026)
    pdf_file = models.FileField(upload_to='reports/monthly/', blank=True, null=True)
    generated_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.college.code} - {self.month}/{self.year}"

class QuarterlyReport(models.Model):
    QUARTER_CHOICES = [
        (1, 'Q1 (Jan-Mar)'),
        (2, 'Q2 (Apr-Jun)'),
        (3, 'Q3 (Jul-Sep)'),
        (4, 'Q4 (Oct-Dec)'),
    ]
    quarter = models.IntegerField(choices=QUARTER_CHOICES)
    year = models.IntegerField(default=2026)
    pdf_file = models.FileField(upload_to='reports/quarterly/', blank=True, null=True)
    ai_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Q{self.quarter} {self.year} Report"

class NewspaperCoverage(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='newspaper_coverage')
    month = models.IntegerField()
    year = models.IntegerField(default=2026)
    publication = models.CharField(max_length=255)
    date = models.DateField()
    edition = models.CharField(max_length=100, blank=True)
    page = models.CharField(max_length=20, blank=True)
    headline = models.CharField(max_length=500, blank=True)
    clipping = models.ImageField(upload_to='newspaper_clippings/', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Newspaper Coverage'
        ordering = ['-date']

    def __str__(self):
        return f"{self.publication} - {self.date}"

class ChannelCoverage(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='channel_coverage')
    month = models.IntegerField()
    year = models.IntegerField(default=2026)
    channel_name = models.CharField(max_length=255)
    platform = models.CharField(max_length=50, blank=True)
    edition = models.CharField(max_length=100, blank=True)
    link = models.URLField(blank=True)

    def __str__(self):
        return f"{self.channel_name} ({self.platform})"

class PressRelease(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='press_releases')
    month = models.IntegerField()
    year = models.IntegerField(default=2026)
    title = models.CharField(max_length=500)
    content = models.TextField()
    date_submitted = models.DateField()
    placements = models.IntegerField(default=0)
    potential_reach = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.title[:100]


class UploadedDocumentReport(models.Model):
    """
    Faculty uploads a large PDF/DOCX report (e.g. 90-100 page detailed report).
    Gemini reads the document natively and condenses it into a professional
    3-month (quarterly) summary report stored as a PDF.
    """
    QUARTER_CHOICES = [
        (1, 'Q1 (Jan–Mar)'),
        (2, 'Q2 (Apr–Jun)'),
        (3, 'Q3 (Jul–Sep)'),
        (4, 'Q4 (Oct–Dec)'),
    ]
    title        = models.CharField(max_length=300, help_text="Short label for this report")
    quarter      = models.IntegerField(choices=QUARTER_CHOICES)
    year         = models.IntegerField(default=2026)
    source_file  = models.FileField(
        upload_to='reports/uploaded_sources/',
        help_text="Upload the original detailed report (PDF or DOCX)"
    )
    ai_summary   = models.TextField(blank=True, help_text="Gemini-generated HTML summary")
    output_pdf   = models.FileField(
        upload_to='reports/doc_quarterly/',
        blank=True, null=True,
        help_text="Auto-generated condensed PDF"
    )
    uploaded_by  = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='uploaded_doc_reports'
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Uploaded Document Report'
        verbose_name_plural = 'Uploaded Document Reports'

    def __str__(self):
        return f"{self.title} — Q{self.quarter} {self.year}"

    def get_quarter_months(self):
        mapping = {1: 'January–March', 2: 'April–June',
                   3: 'July–September', 4: 'October–December'}
        return mapping.get(self.quarter, '')
