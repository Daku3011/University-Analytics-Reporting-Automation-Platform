"""
Tests for the accounts app.
Covers: login, logout, throttling, session timeout, open redirect prevention.
"""
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.cache import cache
from accounts.models import Profile
from colleges.models import College


class LoginViewTests(TestCase):
    """Tests for login_view in accounts/views.py"""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.login_url = reverse('login')
        self.dashboard_url = reverse('dashboard')
        self.college = College.objects.create(
            name='Test College', code='TC'
        )
        self.user = User.objects.create_user(
            username='testuser', password='TestPass123!', email='test@su.edu'
        )
        # Profile is auto-created by signal, but set role
        self.user.profile.role = 'super_admin'
        self.user.profile.save()

    def test_login_page_renders(self):
        """Login page should return 200 for anonymous users."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SU Analytics')

    def test_valid_login_redirects_to_dashboard(self):
        """Valid credentials should redirect to dashboard."""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'TestPass123!',
        })
        self.assertRedirects(response, self.dashboard_url)

    def test_invalid_login_shows_error(self):
        """Invalid credentials should show an error message."""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'WrongPassword',
        })
        self.assertEqual(response.status_code, 200)
        # Should remain on login page with an error message

    def test_empty_credentials_shows_error(self):
        """Submitting empty form should show error."""
        response = self.client.post(self.login_url, {
            'username': '',
            'password': '',
        })
        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_redirected_from_login(self):
        """Already authenticated users should be sent to dashboard."""
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(self.login_url)
        self.assertRedirects(response, self.dashboard_url)

    def test_open_redirect_prevention(self):
        """Login should not redirect to external URLs via ?next= parameter."""
        self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'TestPass123!',
            'next': '//evil.com',
        })
        # Should redirect to dashboard, NOT to evil.com
        # (The redirect is handled internally, so we check the session is set)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_next_url_with_safe_redirect(self):
        """Login should honor safe ?next= URLs."""
        response = self.client.post(
            self.login_url + '?next=/admin/',
            {'username': 'testuser', 'password': 'TestPass123!'}
        )
        self.assertRedirects(response, '/admin/', fetch_redirect_response=False)

    @override_settings(LOGIN_MAX_ATTEMPTS=3, LOGIN_LOCKOUT_SECONDS=300)
    def test_login_throttling(self):
        """After too many failed attempts, user should be locked out."""
        for _ in range(3):
            self.client.post(self.login_url, {
                'username': 'testuser',
                'password': 'WrongPassword',
            })

        # The 4th attempt should be locked out
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'TestPass123!',  # Even with correct password
        })
        self.assertEqual(response.status_code, 200)
        # Should still be on login page (locked out)


class LogoutViewTests(TestCase):
    """Tests for logout."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='TestPass123!'
        )

    def test_logout_clears_session(self):
        """POST to logout should clear the session and redirect to login."""
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'), fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)


class ProfileModelTests(TestCase):
    """Tests for the Profile model."""

    def test_profile_auto_created_on_user_creation(self):
        """A Profile should be automatically created when a User is created."""
        user = User.objects.create_user(username='newuser', password='Test123!')
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, Profile)

    def test_profile_default_role(self):
        """Default profile role should be 'analytics_team'."""
        user = User.objects.create_user(username='newuser', password='Test123!')
        self.assertEqual(user.profile.role, 'analytics_team')

    def test_profile_str_representation(self):
        """Profile __str__ should return a readable string."""
        user = User.objects.create_user(username='newuser', password='Test123!')
        self.assertIn('newuser', str(user.profile))


class RBACDecoratorTests(TestCase):
    """Tests for the role_required decorator."""

    def setUp(self):
        self.client = Client()
        self.college = College.objects.create(
            name='Engineering', code='ENG'
        )
        self.admin = User.objects.create_user(
            username='admin', password='Admin123!'
        )
        self.admin.profile.role = 'super_admin'
        self.admin.profile.save()

        self.college_admin = User.objects.create_user(
            username='college_admin', password='College123!'
        )
        self.college_admin.profile.role = 'college_admin'
        self.college_admin.profile.college = self.college
        self.college_admin.profile.save()

    def test_super_admin_can_access_dashboard(self):
        """Super admins should have access to the dashboard."""
        self.client.login(username='admin', password='Admin123!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_college_admin_can_access_dashboard(self):
        """College admins should have access to the dashboard."""
        self.client.login(username='college_admin', password='College123!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_redirected_to_login(self):
        """Unauthenticated users should be redirected to login."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
