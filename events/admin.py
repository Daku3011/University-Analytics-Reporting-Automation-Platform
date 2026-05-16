from django.contrib import admin
from .models import Event, Media

class MediaInline(admin.TabularInline):
    model = Media
    extra = 1

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'college', 'category', 'date']
    list_filter = ['category', 'college', 'date']
    search_fields = ['title', 'description']
    inlines = [MediaInline]

@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ['event', 'media_type']
    list_filter = ['media_type']
