import pathlib
from django.conf import settings

class PDFService:
    @staticmethod
    def compile_html_to_pdf(html_string, output_path, base_url=None):
        """
        Compiles an HTML string into a PDF using WeasyPrint and writes to output_path.
        WeasyPrint is imported lazily to avoid startup crashes on systems without GTK/Pango.

        base_url resolves relative asset references (e.g. /media/... logos) —
        pass request.build_absolute_uri('/') so embedded images don't silently fail.
        """
        from weasyprint import HTML

        output_path = pathlib.Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        HTML(string=html_string, base_url=base_url).write_pdf(output_path)
        return output_path
