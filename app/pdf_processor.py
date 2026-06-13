from dataclasses import dataclass
from typing import BinaryIO

import fitz


@dataclass
class PDFExtractionResult:
    text: str
    pages: int
    characters: int
    words: int
    preview: str


class PDFProcessingError(Exception):
    """Raised when a PDF cannot be processed safely."""


def extract_text_from_pdf(uploaded_file: BinaryIO) -> PDFExtractionResult:
    """Extract text and useful metrics from a Streamlit uploaded PDF file."""
    try:
        file_bytes = uploaded_file.getvalue()
        document = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise PDFProcessingError(
            "El archivo PDF parece estar corrupto, protegido o no puede abrirse."
        ) from exc

    if document.page_count == 0:
        raise PDFProcessingError("El PDF no contiene paginas para procesar.")

    extracted_pages = []
    for page in document:
        extracted_pages.append(page.get_text("text"))

    text = "\n".join(extracted_pages).strip()
    words = len(text.split())
    preview = text[:1200].strip()

    return PDFExtractionResult(
        text=text,
        pages=document.page_count,
        characters=len(text),
        words=words,
        preview=preview,
    )
