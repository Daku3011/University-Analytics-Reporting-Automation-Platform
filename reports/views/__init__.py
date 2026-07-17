from .dashboard import report_dashboard
from .monthly import generate_monthly, preview_monthly
from .quarterly import generate_quarterly, preview_quarterly
from .compare import compare_reports
from .upload import (
    upload_document_report,
    preview_document_report,
    document_report_processing,
    check_task_status,
    _save_uploaded_file,
)
from .seminar import (
    seminar_dashboard,
    create_seminar_report,
    seminar_report_processing,
    check_seminar_task_status,
    preview_seminar_report,
)
