"""
Resume parsing utilities.
Supports PDF (via PyPDF2) and plain text input.
"""

import io
from typing import Union


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text from a PDF byte stream."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
        return "\n\n".join(pages)
    except Exception as e:
        raise ValueError(f"Could not parse PDF: {e}") from e


def clean_text(text: str) -> str:
    """Normalise whitespace and remove non-printable characters."""
    import re
    # Remove non-printable except newlines and tabs
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", " ", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def parse_resume(file_input: Union[bytes, str], filename: str = "") -> str:
    """
    Accept either raw bytes (from a file upload) or plain text.
    Returns cleaned text ready for the LLM.
    """
    if isinstance(file_input, bytes):
        if filename.lower().endswith(".pdf"):
            raw = extract_text_from_pdf(file_input)
        else:
            # Try UTF-8, fall back to latin-1
            try:
                raw = file_input.decode("utf-8")
            except UnicodeDecodeError:
                raw = file_input.decode("latin-1")
    else:
        raw = file_input

    return clean_text(raw)
