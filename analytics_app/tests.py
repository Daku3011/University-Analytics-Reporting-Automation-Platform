from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from colleges.models import College
from analytics_app.models import MonthlyAnalytics, TopPost
from accounts.models import Profile

class AnalyticsAppTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.college1 = College.objects.create(name="College One", code="CO1")
        self.college2 = College.objects.create(name="College Two", code="CO2")
        
        # Super admin
        self.super_user = User.objects.create_user(username="superadmin", password="password123")
        self.super_user.profile.role = "super_admin"
        self.super_user.profile.save()
        
        # College admin for CO1
        self.college_user = User.objects.create_user(username="collegeadmin", password="password123")
        self.college_user.profile.role = "college_admin"
        self.college_user.profile.college = self.college1
        self.college_user.profile.save()

    def test_add_analytics_renders_form(self):
        self.client.login(username="collegeadmin", password="password123")
        response = self.client.get(reverse('add_analytics'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "College One")

    def test_add_analytics_valid_post(self):
        self.client.login(username="collegeadmin", password="password123")
        response = self.client.post(reverse('add_analytics'), {
            'college': self.college1.id,
            'month': '6',
            'year': '2026',
            'instagram_views': '1500',
            'facebook_views': '1200',
            'instagram_reach': '5000',
            'facebook_reach': '4000',
            'instagram_followers': '300',
            'facebook_followers': '400',
            'youtube_subscribers': '100',
            'followers_gained': '50',
            'reels_count': '10',
            'graphics_count': '5'
        })
        self.assertEqual(MonthlyAnalytics.objects.count(), 1)
        analytics = MonthlyAnalytics.objects.first()
        self.assertEqual(analytics.month, 6)
        self.assertEqual(analytics.year, 2026)
        # Auto-calculated totals
        self.assertEqual(analytics.total_views, 2700)
        self.assertEqual(analytics.total_reach, 9000)
        self.assertRedirects(response, reverse('dashboard'))

    def test_add_analytics_validation_errors(self):
        self.client.login(username="collegeadmin", password="password123")
        
        # Missing month and year
        response = self.client.post(reverse('add_analytics'), {
            'month': '',
            'year': ''
        })
        self.assertRedirects(response, reverse('add_analytics'))
        self.assertEqual(MonthlyAnalytics.objects.count(), 0)

        # Invalid month bounds
        response = self.client.post(reverse('add_analytics'), {
            'month': '13',
            'year': '2026'
        })
        self.assertRedirects(response, reverse('add_analytics'))

        # Non-numeric month
        response = self.client.post(reverse('add_analytics'), {
            'month': 'not-a-month',
            'year': '2026'
        })
        self.assertRedirects(response, reverse('add_analytics'))

    def test_add_analytics_rbac_college_enforcement(self):
        self.client.login(username="collegeadmin", password="password123")
        self.client.post(reverse('add_analytics'), {
            'college': self.college2.id,  # Tries to choose college 2
            'month': '6',
            'year': '2026',
            'instagram_views': '100'
        })
        analytics = MonthlyAnalytics.objects.first()
        # Should be saved for college 1
        self.assertEqual(analytics.college, self.college1)

    def test_add_analytics_save_top_posts(self):
        self.client.login(username="collegeadmin", password="password123")
        response = self.client.post(reverse('add_analytics'), {
            'college': self.college1.id,
            'month': '6',
            'year': '2026',
            'top_ig_1_caption': 'Insta Top Post Caption',
            'top_ig_1_views': '500',
            'top_ig_1_likes': '50',
            'top_ig_1_shares': '5',
            'top_ig_1_link': 'https://instagram.com/p/1',
            
            'top_fb_1_caption': 'FB Top Post Caption',
            'top_fb_1_views': '400',
            'top_fb_1_likes': '40',
            'top_fb_1_shares': '4',
            'top_fb_1_link': 'https://facebook.com/1',
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(TopPost.objects.count(), 2)
        
        ig_post = TopPost.objects.get(platform='instagram')
        self.assertEqual(ig_post.caption, 'Insta Top Post Caption')
        self.assertEqual(ig_post.views, 500)
        self.assertEqual(ig_post.post_link, 'https://instagram.com/p/1')
        
        fb_post = TopPost.objects.get(platform='facebook')
        self.assertEqual(fb_post.caption, 'FB Top Post Caption')
        self.assertEqual(fb_post.views, 400)
        self.assertEqual(fb_post.post_link, 'https://facebook.com/1')

    def test_preview_extracted_data_renders(self):
        self.client.login(username="collegeadmin", password="password123")
        session = self.client.session
        session['extracted_data'] = {
            'detected_college_id': self.college1.id,
            'month': 6,
            'year': 2026,
            'analytics': {
                'instagram_views': 100,
            }
        }
        session.save()
        
        response = self.client.get(reverse('preview_extracted_data'))
        self.assertEqual(response.status_code, 200)

