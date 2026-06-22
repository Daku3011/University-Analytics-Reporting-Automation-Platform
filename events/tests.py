from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from colleges.models import College
from events.models import Event, Media
from accounts.models import Profile

class EventsAppTests(TestCase):
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

    def test_add_event_renders_form(self):
        self.client.login(username="collegeadmin", password="password123")
        response = self.client.get(reverse('add_event'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "College One")

    def test_add_event_valid_post(self):
        self.client.login(username="collegeadmin", password="password123")
        response = self.client.post(reverse('add_event'), {
            'title': 'Test Event Title',
            'description': 'Test Description',
            'category': 'workshop',
            'date': '2026-06-22',
            'college': self.college1.id
        })
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.first()
        self.assertEqual(event.title, 'Test Event Title')
        self.assertEqual(event.college, self.college1)
        self.assertRedirects(response, reverse('event_detail', kwargs={'event_id': event.id}))

    def test_add_event_validation_errors(self):
        self.client.login(username="collegeadmin", password="password123")
        
        # Missing title
        response = self.client.post(reverse('add_event'), {
            'title': '',
            'category': 'workshop',
            'date': '2026-06-22'
        })
        self.assertRedirects(response, reverse('add_event'))
        self.assertEqual(Event.objects.count(), 0)
        
        # Missing date
        response = self.client.post(reverse('add_event'), {
            'title': 'Valid Title',
            'category': 'workshop',
            'date': ''
        })
        self.assertRedirects(response, reverse('add_event'))
        
        # Invalid category
        response = self.client.post(reverse('add_event'), {
            'title': 'Valid Title',
            'category': 'invalid_cat',
            'date': '2026-06-22'
        })
        self.assertRedirects(response, reverse('add_event'))

    def test_add_event_rbac_college_enforcement(self):
        # College admin tries to create event for college 2
        self.client.login(username="collegeadmin", password="password123")
        response = self.client.post(reverse('add_event'), {
            'title': 'Intruder Event',
            'category': 'workshop',
            'date': '2026-06-22',
            'college': self.college2.id  # Tries to assign to college 2
        })
        event = Event.objects.first()
        # Should be auto-assigned to college 1 instead of college 2 because user is college admin for CO1
        self.assertEqual(event.college, self.college1)

    def test_add_event_media_uploads(self):
        self.client.login(username="collegeadmin", password="password123")
        
        # Valid image files
        img_file = SimpleUploadedFile("test.png", b"file_content", content_type="image/png")
        bad_file = SimpleUploadedFile("test.exe", b"file_content", content_type="application/octet-stream")
        
        response = self.client.post(reverse('add_event'), {
            'title': 'Media Test Event',
            'category': 'festival',
            'date': '2026-06-22',
            'media': [img_file, bad_file]
        })
        
        event = Event.objects.get(title='Media Test Event')
        self.assertEqual(event.media.count(), 1)
        filename = event.media.first().file.name.split('/')[-1]
        self.assertTrue(filename.startswith('test'))
        self.assertTrue(filename.endswith('.png'))

    def test_event_detail_permission(self):
        # Create an event for college 2
        event = Event.objects.create(
            title="College 2 Event",
            college=self.college2,
            category="sports",
            date="2026-06-22"
        )
        
        # College admin for CO1 should not be able to view details
        self.client.login(username="collegeadmin", password="password123")
        response = self.client.get(reverse('event_detail', kwargs={'event_id': event.id}))
        self.assertRedirects(response, reverse('dashboard'))
        
        # Super admin should be able to view details
        self.client.login(username="superadmin", password="password123")
        response = self.client.get(reverse('event_detail', kwargs={'event_id': event.id}))
        self.assertEqual(response.status_code, 200)
