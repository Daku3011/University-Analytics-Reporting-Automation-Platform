from django.contrib import admin

from .models import Alert, KpiTarget, MonthlyAnalytics, TopPost


class KpiTargetInline(admin.TabularInline):
    model = KpiTarget
    extra = 0


@admin.register(MonthlyAnalytics)
class MonthlyAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['college', 'department', 'programme', 'month', 'year',
                    'status', 'total_views', 'total_reach', 'followers_gained']
    list_filter = ['college', 'department', 'status', 'month', 'year']

@admin.register(TopPost)
class TopPostAdmin(admin.ModelAdmin):
    list_display = ['college', 'platform', 'views', 'likes', 'month', 'year']
    list_filter = ['platform', 'month', 'year']


@admin.register(KpiTarget)
class KpiTargetAdmin(admin.ModelAdmin):
    list_display = ['college', 'department', 'programme', 'year', 'metric', 'target_value']
    list_filter = ['college', 'metric', 'year']
    search_fields = ['college__name', 'department__name', 'programme__name']


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['level', 'category', 'title', 'college', 'created_at', 'resolved']
    list_filter = ['level', 'category', 'resolved', 'college']
    search_fields = ['title', 'message']
    readonly_fields = ['created_at']
