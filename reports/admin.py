from django.contrib import admin
from .models import MonthlyReport, QuarterlyReport, NewspaperCoverage, ChannelCoverage, PressRelease, UploadedDocumentReport

@admin.register(MonthlyReport)
class MonthlyReportAdmin(admin.ModelAdmin):
    list_display = ['college', 'month', 'year', 'created_at']

@admin.register(QuarterlyReport)
class QuarterlyReportAdmin(admin.ModelAdmin):
    list_display = ['quarter', 'year', 'created_at']

@admin.register(NewspaperCoverage)
class NewspaperCoverageAdmin(admin.ModelAdmin):
    list_display = ['publication', 'date', 'college', 'edition']
    list_filter = ['publication', 'date']

@admin.register(ChannelCoverage)
class ChannelCoverageAdmin(admin.ModelAdmin):
    list_display = ['channel_name', 'platform', 'college', 'month']
    list_filter = ['platform']

@admin.register(PressRelease)
class PressReleaseAdmin(admin.ModelAdmin):
    list_display = ['title', 'college', 'date_submitted', 'placements']
    search_fields = ['title']

@admin.register(UploadedDocumentReport)
class UploadedDocumentReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'quarter', 'year', 'uploaded_by', 'created_at']
    list_filter = ['quarter', 'year']
    search_fields = ['title']
    readonly_fields = ['created_at']
