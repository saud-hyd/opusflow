# Unstructured.io client for document processing
import os
import base64
import tempfile
import requests
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

UNSTRUCTURED_API_KEY = os.getenv("UNSTRUCTURED_API_KEY")
UNSTRUCTURED_API_URL = os.getenv("UNSTRUCTURED_API_URL", "https://api.unstructured.io/general/v0/general")


def extract_from_attachment(filename: str, content_base64: str) -> str:
    """
    Extract text from email attachment using Unstructured.io API.

    Args:
        filename: Attachment filename
        content_base64: Base64 encoded file content

    Returns:
        Extracted text
    """
    if not UNSTRUCTURED_API_KEY:
        return f"[Attachment: {filename} - Unstructured.io not configured]"

    try:
        # Decode and save to temp file
        content = base64.b64decode(content_base64)
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Call Unstructured API
            with open(tmp_path, 'rb') as f:
                response = requests.post(
                    UNSTRUCTURED_API_URL,
                    headers={'unstructured-api-key': UNSTRUCTURED_API_KEY},
                    files={'files': f},
                    timeout=30
                )

            if response.status_code == 200:
                elements = response.json()
                text = '\n'.join([e.get('text', '') for e in elements if e.get('text')])
                return text or f"[No text extracted from {filename}]"
            else:
                return f"[Extraction failed for {filename}]"
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        return f"[Error extracting {filename}: {str(e)}]"
