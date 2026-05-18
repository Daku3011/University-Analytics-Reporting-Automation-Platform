"""
accounts/middleware.py
Session Timeout Middleware — auto-logout users who have been inactive.
"""
import time
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect


class SessionTimeoutMiddleware:
    """
    Tracks each authenticated user's last activity timestamp.
    If the gap exceeds SESSION_COOKIE_AGE, the user is logged out and
    redirected to the login page with a timeout message.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = getattr(settings, 'SESSION_COOKIE_AGE', 3600)

    def __call__(self, request):
        if request.user.is_authenticated:
            last_activity = request.session.get('_last_activity')
            now = time.time()

            if last_activity is not None:
                elapsed = now - last_activity
                if elapsed > self.timeout:
                    logout(request)
                    login_url = getattr(settings, 'LOGIN_URL', '/accounts/login/')
                    # Avoid redirect loops on the login page itself
                    if request.path != login_url:
                        request.session['session_expired'] = True
                        return redirect(login_url)

            # Update last-activity timestamp on every request
            request.session['_last_activity'] = now

        return self.get_response(request)
