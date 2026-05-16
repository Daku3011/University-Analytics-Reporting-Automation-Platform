from django.contrib import admin
from .models import MonthlyAnalytics, TopPost

@admin.register(MonthlyAnalytics)
class MonthlyAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['college', 'month', 'year', 'total_views', 'total_reach', 'followers_gained']
    list_filter = ['college', 'month', 'year']

@admin.register(TopPost)
class TopPostAdmin(admin.ModelAdmin):
    list_display = ['college', 'platform', 'views', 'likes', 'month', 'year']
    list_filter = ['platform', 'month', 'year']
