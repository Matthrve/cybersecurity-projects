"""Extracción de texto crudo desde CVs/vacantes en PDF, DOCX o TXT."""
import io
from pathlib import Path

from pypdf import PdfReader
from docx import Document


def _extension(file) -> str:
    name = getattr(file, "name", None) or str(file)
    return Path(name).suffix.lower()


def extract_text(file) -> str:
    """`file` puede ser una ruta (str/Path) o un objeto tipo Streamlit UploadedFile."""
    ext = _extension(file)
    if hasattr(file, "read"):
        raw = file.read()
        stream = io.BytesIO(raw) if isinstance(raw, bytes) else io.StringIO(raw)
    else:
        stream = open(file, "rb")

    try:
        if ext == ".pdf":
            reader = PdfReader(stream)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if ext == ".docx":
            doc = Document(stream)
            return "\n".join(p.text for p in doc.paragraphs)
        if ext == ".txt":
            data = stream.read()
            return data.decode("utf-8", errors="ignore") if isinstance(data, bytes) else data
        raise ValueError(f"Formato no soportado: {ext}")
    finally:
        stream.close()
