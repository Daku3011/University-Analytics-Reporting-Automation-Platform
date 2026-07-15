import os
import uuid
import pathlib
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock

from colleges.models import College
from accounts.models import Profile
from analytics_app.models import MonthlyAnalytics
from reports.models import MonthlyReport, QuarterlyReport, UploadedDocumentReport
from reports.views import _save_uploaded_file

class ReportsSecurityAndRobustnessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.profile = self.user.profile
        self.profile.role = 'super_admin'
        self.profile.college = None
        self.profile.save()
        self.college = College.objects.create(name='Sarvajanik College of Engineering and Technology', code='SCET')
        
    def login_user(self):
        self.client.login(username='testuser', password='password')

    def test_generate_monthly_get_redirects(self):
        self.login_user()
        response = self.client.get(reverse('generate_monthly'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('report_dashboard'))

    def test_generate_monthly_missing_params(self):
        self.login_user()
        response = self.client.post(reverse('generate_monthly'), {
            'college': self.college.id,
            # 'month' and 'year' are missing
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('report_dashboard'))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Missing required parameters" in str(m) for m in messages))

    def test_generate_monthly_invalid_types(self):
        self.login_user()
        response = self.client.post(reverse('generate_monthly'), {
            'college': self.college.id,
            'month': 'not-a-number',
            'year': '2026'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('report_dashboard'))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("must be valid numeric values" in str(m) for m in messages))

    def test_generate_monthly_invalid_bounds(self):
        self.login_user()
        response = self.client.post(reverse('generate_monthly'), {
            'college': self.college.id,
            'month': '13',
            'year': '2026'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('report_dashboard'))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Month must be between 1 and 12" in str(m) for m in messages))

    def test_generate_monthly_invalid_college(self):
        self.login_user()
        response = self.client.post(reverse('generate_monthly'), {
            'college': 9999,
            'month': '6',
            'year': '2026'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('report_dashboard'))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Specified College does not exist" in str(m) for m in messages))

    @patch('weasyprint.HTML')
    def test_generate_monthly_weasyprint_compilation_failure(self, mock_html):
        self.login_user()
        # Mock HTML().write_pdf to raise an exception
        mock_html.return_value.write_pdf.side_effect = Exception("System library GTK not found")
        
        response = self.client.post(reverse('generate_monthly'), {
            'college': self.college.id,
            'month': '6',
            'year': '2026'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('report_dashboard'))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("PDF compilation failed" in str(m) for m in messages))

    @patch('weasyprint.HTML')
    def test_generate_monthly_success(self, mock_html):
        self.login_user()
        # Ensure we have mock analytics
        MonthlyAnalytics.objects.create(
            college=self.college, month=6, year=2026,
            instagram_views=100, facebook_views=200, total_views=300
        )
        
        response = self.client.post(reverse('generate_monthly'), {
            'college': self.college.id,
            'month': '6',
            'year': '2026'
        })
        
        # Should create a MonthlyReport and redirect to its preview
        report = MonthlyReport.objects.first()
        self.assertIsNotNone(report)
        self.assertEqual(report.college, self.college)
        self.assertEqual(report.month, 6)
        self.assertEqual(report.year, 2026)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('preview_monthly', kwargs={'report_id': report.id}))

    def test_generate_quarterly_missing_params(self):
        self.login_user()
        response = self.client.post(reverse('generate_quarterly'), {
            # 'quarter' is missing
            'year': '2026'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('report_dashboard'))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Missing quarter parameter" in str(m) for m in messages))

    def test_generate_quarterly_invalid_bounds(self):
        self.login_user()
        response = self.client.post(reverse('generate_quarterly'), {
            'quarter': '5',
            'year': '2026'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('report_dashboard'))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Quarter must be between 1 and 4" in str(m) for m in messages))

    @patch('weasyprint.HTML')
    @patch('google.genai.Client')
    def test_generate_quarterly_success(self, mock_client, mock_html):
        self.login_user()
        
        # Mock Gemini response
        mock_response = MagicMock()
        mock_response.text = "<h2>Quarterly Summary HTML</h2>"
        mock_client.return_value.models.generate_content.return_value = mock_response
        
        response = self.client.post(reverse('generate_quarterly'), {
            'quarter': '1',
            'year': '2026'
        })
        
        # Should create a QuarterlyReport and redirect to its preview
        report = QuarterlyReport.objects.first()
        self.assertIsNotNone(report)
        self.assertEqual(report.quarter, 1)
        self.assertEqual(report.year, 2026)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('preview_quarterly', kwargs={'report_id': report.id}))

    def test_compare_reports_missing_params(self):
        self.login_user()
        response = self.client.post(reverse('compare_reports'), {
            'college': self.college.id,
            # month_a and month_b are missing
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Missing required fields for comparison", response.context['comparison_html'])

    def test_compare_reports_invalid_bounds(self):
        self.login_user()
        response = self.client.post(reverse('compare_reports'), {
            'college': self.college.id,
            'month_a': '0',
            'month_b': '13',
            'year': '2026'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Months must be between 1 and 12", response.context['comparison_html'])

    @patch('google.genai.Client')
    def test_compare_reports_success(self, mock_client):
        self.login_user()
        
        # Mock Gemini MoM comparison response
        mock_response = MagicMock()
        mock_response.text = "<h2>Comparison Summary</h2>"
        mock_client.return_value.models.generate_content.return_value = mock_response
        
        response = self.client.post(reverse('compare_reports'), {
            'college': self.college.id,
            'month_a': '1',
            'month_b': '2',
            'year': '2026'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['comparison_html'])
        self.assertIn("Comparison Summary", response.context['comparison_html'])

    def test_save_uploaded_file_path_traversal(self):
        # Create a mock file with a malicious name containing path traversal payloads
        malicious_filename = "../../../etc/passwd.pdf"
        file_content = b"%PDF-1.4 mock content"
        uploaded_file = SimpleUploadedFile(malicious_filename, file_content, content_type='application/pdf')
        
        # Invoke _save_uploaded_file
        save_path, rel_path = _save_uploaded_file(uploaded_file, "prefix")
        
        # The file stem must be fully sanitized and not escape the uploaded_sources boundaries
        self.assertTrue(save_path.exists())
        self.assertNotIn("..", save_path.name)
        self.assertNotIn("/", save_path.name)
        self.assertNotIn("etc", str(save_path.parent.relative_to(save_path.parent.parent)))
        self.assertTrue(save_path.name.endswith(".pdf"))
        
        # Clean up the created physical file
        if save_path.exists():
            save_path.unlink()


class AnnualAnalyzerTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.profile = self.user.profile
        self.profile.role = 'super_admin'
        self.profile.save()
        
    def login_user(self):
        self.client.login(username='testuser', password='password')
        
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('annual_analyzer'))
        self.assertEqual(response.status_code, 302)
        
    def test_dashboard_authenticated(self):
        self.login_user()
        response = self.client.get(reverse('annual_analyzer'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/annual_analyzer.html')
        
    def test_ajax_upload_invalid_category(self):
        self.login_user()
        pdf_file = SimpleUploadedFile("test.pdf", b"pdfcontent", content_type="application/pdf")
        response = self.client.post(reverse('ajax_upload_batch_file'), {
            'file': pdf_file,
            'category': 'invalid_cat'
        })
        self.assertEqual(response.status_code, 400)
        
    @patch('reports.tasks.process_batch_file_task.delay')
    def test_ajax_upload_success(self, mock_task):
        self.login_user()
        pdf_file = SimpleUploadedFile("test_social.pdf", b"pdfcontent", content_type="application/pdf")
        response = self.client.post(reverse('ajax_upload_batch_file'), {
            'file': pdf_file,
            'category': 'social_media'
        })
        self.assertEqual(response.status_code, 200)
        from reports.models import BatchUploadFile
        self.assertEqual(BatchUploadFile.objects.count(), 1)
        uploaded = BatchUploadFile.objects.first()
        self.assertEqual(uploaded.category, 'social_media')
        self.assertEqual(uploaded.filename, 'test_social.pdf')
        mock_task.assert_called_once_with(uploaded.id)
        
        # Cleanup
        if uploaded.file and pathlib.Path(uploaded.file.path).exists():
            pathlib.Path(uploaded.file.path).unlink()

