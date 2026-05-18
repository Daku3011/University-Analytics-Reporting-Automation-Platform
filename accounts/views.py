from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.cache import cache
from django.conf import settings


def login_view(request):
    # Already authenticated → go to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')

    # Check if session expired (set by middleware)
    session_expired = request.session.pop('session_expired', False)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')

        # ── Login Throttling ─────────────────────────────────────────
        max_attempts = getattr(settings, 'LOGIN_MAX_ATTEMPTS', 5)
        lockout_secs = getattr(settings, 'LOGIN_LOCKOUT_SECONDS', 900)
        lockout_key = f'login_lockout_{username}'
        attempts_key = f'login_attempts_{username}'

        # Check if account is currently locked out
        if cache.get(lockout_key):
            remaining = cache.ttl(lockout_key) if hasattr(cache, 'ttl') else lockout_secs
            return render(request, 'accounts/login.html', {
                'error': f'Too many failed attempts. Account locked. Please try again in 15 minutes.',
                'locked': True,
            })

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Successful login — clear failed attempts
            cache.delete(attempts_key)
            login(request, user)

            # Handle "Remember Me" — extend session to 7 days
            if remember_me:
                request.session.set_expiry(60 * 60 * 24 * 7)
            else:
                request.session.set_expiry(0)  # Expires when browser closes

            # Redirect to intended page (supports ?next= parameter)
            next_url = request.GET.get('next') or request.POST.get('next', '')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect('dashboard')

        else:
            # Failed login — increment counter
            attempts = cache.get(attempts_key, 0) + 1
            cache.set(attempts_key, attempts, lockout_secs)

            if attempts >= max_attempts:
                cache.set(lockout_key, True, lockout_secs)
                error = f'Too many failed attempts. Account locked for 15 minutes.'
            else:
                remaining_attempts = max_attempts - attempts
                error = f'Invalid username or password. {remaining_attempts} attempt{"s" if remaining_attempts != 1 else ""} remaining.'

            return render(request, 'accounts/login.html', {'error': error})

    return render(request, 'accounts/login.html', {
        'session_expired': session_expired,
    })


@require_POST
def logout_view(request):
    """POST-only logout with CSRF protection."""
    logout(request)
    return redirect('login')
