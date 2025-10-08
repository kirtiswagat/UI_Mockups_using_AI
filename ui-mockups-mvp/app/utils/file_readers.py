from pathlib import Path
from docx import Document as DocxDocument
from PyPDF2 import PdfReader

def read_file_text(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix in [".txt", ".md"]:
        return uploaded_file.read().decode("utf-8", errors="ignore")
    if suffix == ".docx":
        doc = DocxDocument(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])
    if suffix == ".pdf":
        reader = PdfReader(uploaded_file)
        out = []
        for page in reader.pages:
            out.append(page.extract_text() or "")
        return "\n".join(out)
    # fallback: try decoding
    try:
        return uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""
