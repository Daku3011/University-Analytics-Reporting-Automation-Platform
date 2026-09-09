from django.core.management.base import BaseCommand
from django.db import transaction
from colleges.models import College
from reports.models import MonthlyReport, UploadedDocumentReport
import random
from datetime import datetime


class Command(BaseCommand):
    help = 'Adds dummy data to the database for development/testing purposes'

    def handle(self, *args, **options):
        self.stdout.write("Adding dummy data to database...")

        colleges = College.objects.all()
        if not colleges.exists():
            self.stdout.write(self.style.ERROR("No colleges found. Please run seed_data first."))
            return

        with transaction.atomic():
            # Add dummy MonthlyReport entries
            # One per college per month for current year
            current_year = datetime.now().year
            months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

            for college in colleges:
                for month in months:
                    # Create 1-2 reports per college per month for variety
                    num_reports = random.randint(1, 2)
                    for _ in range(num_reports):
                        MonthReport, created = MonthlyReport.objects.get_or_create(
                            college=college,
                            month=month,
                            year=current_year,
                            defaults={
                                'pdf_file': None,
                                'generated_text': '',
                                'report_title': f"Monthly Report - {college.name} - Month {month}",
                                'prepared_by': f"Staff {random.randint(1, 10)}",
                            }
                        )
                        if created:
                            self.stdout.write(
                                f"Created MonthlyReport: {college.code} - Month {month}/{current_year}"
                            )

            # Add dummy UploadedDocumentReport entries
            # One per quarter for current year
            quarters = [1, 2, 3, 4]
            for college in colleges:
                for quarter in quarters:
                    # Create UploadedDocumentReport with dummy data
                    # source_file_1 is required, source_file_2 and source_file_3 are optional
                    UploadedDocumentReport.objects.get_or_create(
                        title=f"Quarterly Summary - {college.code} Q{quarter}",
                        quarter=quarter,
                        year=current_year,
                        defaults={
                            'source_file_1': f'reports/uploaded_sources/month_{college.code}_{quarter}_1.pdf',
                            'source_file_2': f'reports/uploaded_sources/month_{college.code}_{quarter}_2.pdf' if random.random() > 0.5 else None,
                            'source_file_3': f'reports/uploaded_sources/month_{college.code}_{quarter}_3.pdf' if random.random() > 0.7 else None,
                            'ai_summary': '',
                            'output_pdf': None,
                            'uploaded_by': None,
                        }
                    )
                    self.stdout.write(
                        f"Created UploadedDocumentReport: {college.code} Q{quarter}/{current_year}"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Dummy data added successfully for {colleges.count()} colleges"
            )
        )