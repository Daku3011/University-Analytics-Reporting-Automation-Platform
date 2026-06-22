import os
from google import genai

def main():
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get('GEMINI_API_KEY')

    client = genai.Client(api_key=api_key)

    print("API Key prefix:", api_key[:10] if api_key else "None")

    # Use a small test PDF
    test_pdf = "test_doc.pdf"
    with open(test_pdf, "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000219 00000 n \n0000000307 00000 n \ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n402\n%%EOF")

    print("Uploading to Gemini...")
    gfile = client.files.upload(file=test_pdf)

    import time
    while gfile.state.name == 'PROCESSING':
        print("Waiting for file to be active...")
        time.sleep(2)
        gfile = client.files.get(name=gfile.name)

    print("File state:", gfile.state.name)

    try:
        print("Calling generate_content with mixed list...")
        map_prompt = "Extract text from this file."
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[gfile, map_prompt]
        )
        print("Response:", resp.text)
    except Exception as e:
        print("Error:", repr(e))
    finally:
        client.files.delete(name=gfile.name)
        print("Deleted file.")

if __name__ == "__main__":
    main()
