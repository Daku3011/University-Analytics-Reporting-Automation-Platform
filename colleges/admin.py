from django.contrib import admin

from .models import College, Department, Programme, University


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'short_name']
    search_fields = ['name', 'code']


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'university']
    list_filter = ['university']
    search_fields = ['name', 'code']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'college']
    list_filter = ['college']
    search_fields = ['name', 'code']


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'department']
    list_filter = ['department__college']
    search_fields = ['name', 'code']
