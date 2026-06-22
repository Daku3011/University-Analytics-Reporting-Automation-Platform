import os
import time
from django.conf import settings
from google import genai
from google.genai import types as genai_types

class GeminiService:
    @staticmethod
    def get_client():
        api_key = os.environ.get('GEMINI_API_KEY', '')
        return genai.Client(api_key=api_key)

    @classmethod
    def generate_content(cls, prompt, model_name=None):
        """Generates content from Gemini using the provided prompt."""
        if not model_name:
            gemini_config = getattr(settings, 'GEMINI_CONFIG', {})
            model_name = gemini_config.get('MODEL', 'gemini-2.5-flash')

        client = cls.get_client()
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                http_options={'timeout': 600000}
            )
        )
        return response.text or ''

    @classmethod
    def upload_and_wait(cls, file_path):
        """
        Uploads a PDF file to Gemini Files API and polls until ACTIVE.
        Returns the uploaded file object.
        """
        client = cls.get_client()
        uploaded = client.files.upload(
            file=str(file_path),
            config=genai_types.UploadFileConfig(
                mime_type='application/pdf',
                display_name=file_path.name
            )
        )

        max_wait = 300
        waited = 0
        while uploaded.state.name == 'PROCESSING' and waited < max_wait:
            time.sleep(5)
            waited += 5
            uploaded = client.files.get(name=uploaded.name)

        if uploaded.state.name != 'ACTIVE':
            raise Exception(
                f"Gemini file processing failed or timed out for {file_path.name}. "
                f"Final state: {uploaded.state.name}"
            )

        return uploaded

    @classmethod
    def delete_file(cls, file_name):
        """Deletes a file from Gemini Files API by name."""
        client = cls.get_client()
        try:
            client.files.delete(name=file_name)
        except Exception:
            pass
