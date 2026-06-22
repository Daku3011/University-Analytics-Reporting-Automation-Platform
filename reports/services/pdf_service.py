import pathlib
from django.conf import settings

class PDFService:
    @staticmethod
    def compile_html_to_pdf(html_string, output_path):
        """
        Compiles an HTML string into a PDF using WeasyPrint and writes to output_path.
        WeasyPrint is imported lazily to avoid startup crashes on systems without GTK/Pango.
        """
        from weasyprint import HTML
        
        output_path = pathlib.Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        HTML(string=html_string).write_pdf(output_path)
        return output_path
