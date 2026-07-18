from django.db import models
from colleges.models import College
import datetime
from su_analytics.constants import MONTH_CHOICES, QUARTER_CHOICES, QUARTER_MONTHS

def get_current_year():
    return datetime.date.today().year

class MonthlyReport(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='monthly_reports')
    month = models.IntegerField(choices=MONTH_CHOICES)
    year = models.IntegerField(default=get_current_year)
    pdf_file = models.FileField(upload_to='reports/monthly/', blank=True, null=True)
    generated_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['college', 'month', 'year'], name='unique_monthly_report')
        ]
        indexes = [
            models.Index(fields=['year', 'month'], name='idx_monthlyreport_year_month'),
        ]

    def __str__(self):
        return f"{self.college.code} - {self.month}/{self.year}"

class QuarterlyReport(models.Model):
    quarter = models.IntegerField(choices=QUARTER_CHOICES)
    year = models.IntegerField(default=get_current_year)
    pdf_file = models.FileField(upload_to='reports/quarterly/', blank=True, null=True)
    ai_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Q{self.quarter} {self.year} Report"

class NewspaperCoverage(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='newspaper_coverage')
    month = models.IntegerField(choices=MONTH_CHOICES)
    year = models.IntegerField(default=get_current_year)
    publication = models.CharField(max_length=255)
    date = models.DateField()
    edition = models.CharField(max_length=100, blank=True)
    page = models.CharField(max_length=20, blank=True)
    headline = models.CharField(max_length=500, blank=True)
    clipping = models.ImageField(upload_to='newspaper_clippings/', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Newspaper Coverage'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['college', 'month', 'year'], name='idx_newspaper_col_month_year'),
            models.Index(fields=['year', 'month'], name='idx_newspaper_year_month'),
        ]

    def __str__(self):
        return f"{self.publication} - {self.date}"

class ChannelCoverage(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='channel_coverage')
    month = models.IntegerField(choices=MONTH_CHOICES)
    year = models.IntegerField(default=get_current_year)
    channel_name = models.CharField(max_length=255)
    platform = models.CharField(max_length=50, blank=True)
    edition = models.CharField(max_length=100, blank=True)
    link = models.URLField(blank=True)

    class Meta:
        ordering = ['-year', '-month']
        indexes = [
            models.Index(fields=['college', 'month', 'year'], name='idx_channel_col_month_year'),
        ]

    def __str__(self):
        return f"{self.channel_name} ({self.platform})"

class PressRelease(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='press_releases')
    month = models.IntegerField(choices=MONTH_CHOICES)
    year = models.IntegerField(default=get_current_year)
    title = models.CharField(max_length=500)
    content = models.TextField()
    date_submitted = models.DateField()
    placements = models.IntegerField(default=0)
    potential_reach = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['-year', '-month']
        indexes = [
            models.Index(fields=['college', 'month', 'year'], name='idx_pr_col_month_year'),
            models.Index(fields=['year', 'month'], name='idx_pressrelease_year_month'),
        ]

    def __str__(self):
        return self.title[:100]


class UploadedDocumentReport(models.Model):
    """
    Faculty uploads up to 3 monthly PDF reports (e.g. Jan + Feb + Mar, each up to 70 MB).
    Gemini reads all 3 via the Files API and condenses them into a professional
    3-month quarterly summary report stored as a PDF.
    """
    title        = models.CharField(max_length=300, help_text="Short label for this report")
    quarter      = models.IntegerField(choices=QUARTER_CHOICES)
    year         = models.IntegerField(default=get_current_year)

    # One file per month — only month 1 is required
    source_file_1 = models.FileField(
        upload_to='reports/uploaded_sources/',
        help_text="Month 1 report PDF (required)"
    )
    source_file_2 = models.FileField(
        upload_to='reports/uploaded_sources/',
        blank=True, null=True,
        help_text="Month 2 report PDF (optional)"
    )
    source_file_3 = models.FileField(
        upload_to='reports/uploaded_sources/',
        blank=True, null=True,
        help_text="Month 3 report PDF (optional)"
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
        indexes = [
            models.Index(fields=['year', 'quarter'], name='idx_uploadeddoc_year_quarter'),
        ]

    def __str__(self):
        return f"{self.title} — Q{self.quarter} {self.year}"

    def get_quarter_months(self):
        mapping = {1: 'January–March', 2: 'April–June',
                   3: 'July–September', 4: 'October–December'}
        return mapping.get(self.quarter, '')

    def get_month_names(self):
        return self.QUARTER_MONTHS.get(self.quarter, ('Month 1', 'Month 2', 'Month 3'))

    def uploaded_files_count(self):
        return sum(1 for f in [self.source_file_1, self.source_file_2, self.source_file_3] if f)

