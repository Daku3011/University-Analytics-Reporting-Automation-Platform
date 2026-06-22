"""
RBAC decorators for SU Analytics.

Usage:
    @role_required('super_admin')
    def admin_only_view(request): ...

    @role_required('super_admin', 'college_admin')
    def admin_or_college_view(request): ...
"""
from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


def role_required(*allowed_roles):
    """
    Decorator that checks the user's profile.role against the allowed roles.
    Super admins always have access. Returns 403 if the user lacks permission.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            # Superusers always pass
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            profile = getattr(request.user, 'profile', None)
            if profile is None:
                return HttpResponseForbidden(
                    '<h2>403 Forbidden</h2>'
                    '<p>Your account does not have a profile assigned. '
                    'Contact an administrator.</p>'
                )

            if profile.role not in allowed_roles and 'super_admin' not in [profile.role]:
                return HttpResponseForbidden(
                    '<h2>403 Forbidden</h2>'
                    '<p>You do not have permission to access this page. '
                    f'Required role: {", ".join(allowed_roles)}.</p>'
                )

            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def get_user_college(user):
    """
    Returns the college associated with the user, or None for super admins.
    Useful for filtering querysets by the user's assigned college.
    """
    profile = getattr(user, 'profile', None)
    if profile and profile.role != 'super_admin':
        return profile.college
    return None


def college_queryset_filter(queryset, user, college_field='college'):
    """
    Filters a queryset by the user's assigned college.
    Super admins see all data. College admins see only their college's data.

    Usage:
        events = college_queryset_filter(Event.objects.all(), request.user)
    """
    college = get_user_college(user)
    if college is not None:
        if college_field in ('id', 'pk') or queryset.model.__name__ == 'College':
            return queryset.filter(id=college.id)
        return queryset.filter(**{college_field: college})
    return queryset

