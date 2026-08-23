from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from colleges.models import College, Department, Programme
from analytics_app.models import MonthlyAnalytics, TopPost, KpiTarget
from analytics_app.services.comparisons import (
    pct_change, build_yoy_comparison, build_institute_ranking,
)
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


class ComparisonServiceTests(TestCase):
    """Unit tests for the comparison/trend service (#3)."""

    def setUp(self):
        self.co1 = College.objects.create(name="Alpha College", code="CO1")
        self.co2 = College.objects.create(name="Beta College", code="CO2")

    @staticmethod
    def _add(college, year, month, ig_views, fb_views=0, reach_ig=0, reach_fb=0):
        MonthlyAnalytics.objects.create(
            college=college, month=month, year=year,
            instagram_views=ig_views, facebook_views=fb_views,
            instagram_reach=reach_ig, facebook_reach=reach_fb,
            followers_gained=10,
        )

    def test_pct_change(self):
        self.assertEqual(pct_change(150, 100), 50.0)
        self.assertEqual(pct_change(50, 100), -50.0)
        self.assertEqual(pct_change(100, 100), 0.0)
        # No baseline → None (rendered as an em-dash, not a misleading %)
        self.assertIsNone(pct_change(10, 0))
        self.assertIsNone(pct_change(10, None))

    def test_yoy_month_rows_and_totals(self):
        self._add(self.co1, 2025, 1, 60, fb_views=40)   # total 100
        self._add(self.co1, 2025, 2, 120, fb_views=80)  # total 200
        self._add(self.co1, 2026, 1, 100, fb_views=50)  # total 150
        self._add(self.co1, 2026, 2, 200, fb_views=100)  # total 300

        yoy = build_yoy_comparison(self.co1, 2026, 'total_views')
        self.assertEqual(len(yoy['months']), 12)
        jan = next(m for m in yoy['months'] if m['num'] == 1)
        feb = next(m for m in yoy['months'] if m['num'] == 2)
        self.assertEqual((jan['current'], jan['previous'], jan['change']), (150, 100, 50.0))
        self.assertEqual((feb['current'], feb['previous'], feb['change']), (300, 200, 50.0))
        self.assertEqual(yoy['selected_summary']['current'], 450)
        self.assertEqual(yoy['selected_summary']['previous'], 300)
        self.assertEqual(yoy['prev_year'], 2025)

    def test_yoy_best_month_and_average(self):
        self._add(self.co1, 2026, 1, 100)
        self._add(self.co1, 2026, 3, 300)
        yoy = build_yoy_comparison(self.co1, 2026, 'total_views')
        self.assertEqual(yoy['best_month'], {'label': 'March', 'value': 300})
        self.assertEqual(yoy['monthly_average'], 200)
        self.assertEqual(yoy['months_with_data'], 2)

    def test_yoy_no_previous_year_gives_none_changes(self):
        self._add(self.co1, 2026, 1, 500)
        yoy = build_yoy_comparison(self.co1, 2026, 'total_views')
        self.assertIsNone(yoy['selected_summary']['change'])
        self.assertTrue(all(m['change'] is None for m in yoy['months']))

    def test_institute_ranking_orders_shares_and_ranks(self):
        self._add(self.co1, 2026, 1, 450)          # CO1 total 450
        self._add(self.co2, 2026, 1, 900)          # CO2 total 900

        ranking = build_institute_ranking(College.objects.all(), 2026, 'total_views')
        rows = ranking['rows']
        self.assertEqual([r['college_code'] for r in rows], ['CO2', 'CO1'])
        self.assertEqual([r['rank'] for r in rows], [1, 2])
        shares = sum(r['share_pct'] for r in rows)
        self.assertAlmostEqual(shares, 100.0, places=0)
        self.assertEqual(ranking['university_total'], 1350)
        self.assertEqual(ranking['top_performer']['college_code'], 'CO2')

    def test_institute_ranking_excludes_breakdown_rows(self):
        # Department-level rows must not inflate institute totals
        dept = Department.objects.create(college=self.co1, name="Computer")
        MonthlyAnalytics.objects.create(
            college=self.co1, department=dept, month=1, year=2026,
            instagram_views=9999,
        )
        self._add(self.co1, 2026, 1, 100)
        ranking = build_institute_ranking(College.objects.all(), 2026, 'total_views')
        co1 = next(r for r in ranking['rows'] if r['college_code'] == 'CO1')
        self.assertEqual(co1['total'], 100)


class ComparisonViewTests(TestCase):
    """RBAC + rendering checks for /analytics/compare/ (#3)."""

    def setUp(self):
        self.client = Client()
        self.co1 = College.objects.create(name="Alpha College", code="CO1")
        self.co2 = College.objects.create(name="Beta College", code="CO2")
        MonthlyAnalytics.objects.create(
            college=self.co1, month=1, year=2026, instagram_views=400,
        )
        MonthlyAnalytics.objects.create(
            college=self.co2, month=1, year=2026, instagram_views=800,
        )
        self.super_user = User.objects.create_user(username="superadmin", password="password123")
        self.super_user.profile.role = "super_admin"
        self.super_user.profile.save()
        self.college_user = User.objects.create_user(username="collegeadmin", password="password123")
        self.college_user.profile.role = "college_admin"
        self.college_user.profile.college = self.co1
        self.college_user.profile.save()

    def test_yoy_mode_renders_for_super_admin(self):
        self.client.login(username="superadmin", password="password123")
        resp = self.client.get(reverse('comparison_view'), {'mode': 'yoy', 'year': 2026})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Year-on-Year')

    def test_invalid_metric_falls_back(self):
        self.client.login(username="superadmin", password="password123")
        resp = self.client.get(
            reverse('comparison_view'), {'mode': 'institute', 'metric': 'DROP TABLE'})
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'DROP TABLE')

    def test_super_admin_sees_full_ranking(self):
        self.client.login(username="superadmin", password="password123")
        resp = self.client.get(reverse('comparison_view'), {'mode': 'institute', 'year': 2026})
        self.assertContains(resp, 'Alpha College')
        self.assertContains(resp, 'Beta College')

    def test_college_admin_sees_only_own_row_in_ranking(self):
        self.client.login(username="collegeadmin", password="password123")
        resp = self.client.get(reverse('comparison_view'), {'mode': 'institute', 'year': 2026})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Alpha College')
        self.assertNotContains(resp, 'Beta College')
        # Chart payload must be null for scoped users — a real series would leak the ranking
        self.assertIn(b'<script id="cmp-chart-data" type="application/json">null</script>',
                      resp.content)


class KpiGapUniversityRollupTests(TestCase):
    """?college=all university-wide KPI roll-up (#1)."""

    def setUp(self):
        self.client = Client()
        self.co1 = College.objects.create(name="Alpha College", code="CO1")
        self.co2 = College.objects.create(name="Beta College", code="CO2")
        KpiTarget.objects.create(college=self.co1, year=2026, metric='total_views', target_value=1000)
        KpiTarget.objects.create(college=self.co2, year=2026, metric='total_reach', target_value=500)
        MonthlyAnalytics.objects.create(
            college=self.co1, month=1, year=2026, instagram_views=250, facebook_views=0,
        )
        self.super_user = User.objects.create_user(username="superadmin", password="password123")
        self.super_user.profile.role = "super_admin"
        self.super_user.profile.save()
        self.college_user = User.objects.create_user(username="collegeadmin", password="password123")
        self.college_user.profile.role = "college_admin"
        self.college_user.profile.college = self.co1
        self.college_user.profile.save()

    def test_super_admin_sees_all_colleges_rollup(self):
        self.client.login(username="superadmin", password="password123")
        resp = self.client.get(reverse('kpi_gap_view'), {'college': 'all', 'year': 2026})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'All Colleges')
        self.assertContains(resp, 'CO1')
        self.assertContains(resp, 'CO2')
        self.assertContains(resp, '25.0')  # 250/1000 achievement

    def test_college_admin_stays_scoped_to_own_college(self):
        self.client.login(username="collegeadmin", password="password123")
        resp = self.client.get(reverse('kpi_gap_view'), {'college': 'all', 'year': 2026})
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'CO2')


class HierarchyTests(TestCase):
    """University → Institute → Department → Programme drill-down (#4)."""

    def setUp(self):
        self.client = Client()
        self.co1 = College.objects.create(name="Alpha College", code="CO1")
        self.co2 = College.objects.create(name="Beta College", code="CO2")
        self.dept1 = Department.objects.create(college=self.co1, name="Computer", code="CE")
        self.prog1 = Programme.objects.create(department=self.dept1, name="B.Tech CSE", code="BTCE")
        # Beta's hierarchy — used for cross-college 403 checks
        self.dept2 = Department.objects.create(college=self.co2, name="Management", code="MGT")
        self.prog2 = Programme.objects.create(department=self.dept2, name="MBA", code="MBA")

        MonthlyAnalytics.objects.create(
            college=self.co1, month=1, year=2026, instagram_views=100)
        MonthlyAnalytics.objects.create(
            college=self.co1, department=self.dept1, month=1, year=2026,
            instagram_views=55)
        MonthlyAnalytics.objects.create(
            college=self.co1, department=self.dept1, programme=self.prog1,
            month=1, year=2026, instagram_views=40)

        self.super_user = User.objects.create_user(username="superadmin", password="password123")
        self.super_user.profile.role = "super_admin"
        self.super_user.profile.save()
        self.college_user = User.objects.create_user(username="collegeadmin", password="password123")
        self.college_user.profile.role = "college_admin"
        self.college_user.profile.college = self.co1
        self.college_user.profile.save()

    def test_full_drilldown_chain_renders(self):
        self.client.login(username="superadmin", password="password123")
        r1 = self.client.get(reverse('university_overview'))
        self.assertEqual(r1.status_code, 200)
        self.assertContains(r1, 'Alpha College')
        self.assertContains(r1, 'Beta College')

        r2 = self.client.get(reverse('college_detail', args=[self.co1.id]))
        self.assertEqual(r2.status_code, 200)
        self.assertContains(r2, 'Computer')

        r3 = self.client.get(reverse('department_detail', args=[self.dept1.id]))
        self.assertEqual(r3.status_code, 200)
        self.assertContains(r3, 'B.Tech CSE')

        r4 = self.client.get(reverse('programme_detail', args=[self.prog1.id]))
        self.assertEqual(r4.status_code, 200)

    def test_university_overview_excludes_breakdown_rows(self):
        self.client.login(username="superadmin", password="password123")
        resp = self.client.get(reverse('university_overview'), {'year': 2026})
        # Only the institute-level row (100) counts; dept/prog rows (55+40) must not inflate
        self.assertContains(resp, '100')

    def test_cross_college_access_forbidden(self):
        self.client.login(username="collegeadmin", password="password123")
        self.assertEqual(
            self.client.get(reverse('college_detail', args=[self.co2.id])).status_code, 403)
        self.assertEqual(
            self.client.get(reverse('department_detail', args=[self.dept2.id])).status_code, 403)
        self.assertEqual(
            self.client.get(reverse('programme_detail', args=[self.prog2.id])).status_code, 403)

    def test_entry_form_exposes_hierarchy_selects(self):
        self.client.login(username="collegeadmin", password="password123")
        resp = self.client.get(reverse('add_analytics'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'id_department')
        self.assertContains(resp, 'id_programme')

    def test_department_bucket_landing(self):
        self.client.login(username="collegeadmin", password="password123")
        resp = self.client.post(reverse('add_analytics'), {
            'college': self.co1.id, 'month': '6', 'year': '2026',
            'department': str(self.dept1.id),
            'instagram_views': '500',
        })
        self.assertRedirects(resp, reverse('dashboard'))
        row = MonthlyAnalytics.objects.get(
            college=self.co1, department=self.dept1, programme=None,
            month=6, year=2026)
        self.assertEqual(row.total_views, 500)

    def test_programme_bucket_landing(self):
        self.client.login(username="collegeadmin", password="password123")
        self.client.post(reverse('add_analytics'), {
            'college': self.co1.id, 'month': '6', 'year': '2026',
            'department': str(self.dept1.id), 'programme': str(self.prog1.id),
            'instagram_views': '300',
        })
        row = MonthlyAnalytics.objects.get(
            college=self.co1, department=self.dept1, programme=self.prog1,
            month=6, year=2026)
        self.assertEqual(row.total_views, 300)

    def test_mismatched_department_rejected(self):
        self.client.login(username="collegeadmin", password="password123")
        resp = self.client.post(reverse('add_analytics'), {
            'college': self.co1.id, 'month': '7', 'year': '2026',
            'department': str(self.dept2.id),  # belongs to CO2
            'instagram_views': '999',
        })
        self.assertRedirects(resp, reverse('add_analytics'))
        self.assertFalse(MonthlyAnalytics.objects.filter(month=7, year=2026).exists())

    def test_mismatched_programme_rejected(self):
        self.client.login(username="collegeadmin", password="password123")
        resp = self.client.post(reverse('add_analytics'), {
            'college': self.co1.id, 'month': '7', 'year': '2026',
            'department': str(self.dept1.id),
            'programme': str(self.prog2.id),  # lives under CO2's department
            'instagram_views': '999',
        })
        self.assertRedirects(resp, reverse('add_analytics'))
        self.assertFalse(MonthlyAnalytics.objects.filter(month=7, year=2026).exists())

    def test_preview_save_lands_in_department_bucket(self):
        self.client.login(username="collegeadmin", password="password123")
        session = self.client.session
        session['extracted_data'] = {
            'detected_college_id': self.co1.id,
            'month': 6, 'year': 2026,
            'analytics': {'instagram_views': 100},
        }
        session.save()
        resp = self.client.post(reverse('preview_extracted_data'), {
            'college': self.co1.id, 'month': '6', 'year': '2026',
            'department': str(self.dept1.id),
        })
        self.assertRedirects(resp, reverse('dashboard'))
        row = MonthlyAnalytics.objects.get(
            college=self.co1, department=self.dept1, programme=None,
            month=6, year=2026)
        self.assertEqual(row.instagram_views, 100)

