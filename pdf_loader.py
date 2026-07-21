"""
Carga y extracción de texto de archivos PDF.

Recorre una carpeta buscando archivos .pdf y devuelve el texto de cada
página junto con metadatos (nombre de archivo y número de página), para
que la capa de indexado (text_index.py) pueda trocearlo y buscarlo.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger(__name__)


@dataclass
class PageText:
    source: str       # nombre del archivo PDF
    page_number: int  # 1-indexado
    text: str


def list_pdf_files(folder: str | Path) -> list[Path]:
    folder = Path(folder)
    if not folder.exists():
        return []
    return sorted(p for p in folder.glob("*.pdf") if p.is_file())


def extract_pages(pdf_path: str | Path) -> list[PageText]:
    """Extrae el texto de cada página de un PDF individual."""
    pdf_path = Path(pdf_path)
    pages: list[PageText] = []

    try:
        reader = PdfReader(str(pdf_path))
    except Exception as exc:  # PDF corrupto o ilegible
        logger.warning("No se pudo abrir %s: %s", pdf_path.name, exc)
        return pages

    for i, page in enumerate(reader.pages, start=1):
        try:
            raw = page.extract_text() or ""
        except Exception as exc:
            logger.warning("Fallo extrayendo texto de %s (página %d): %s", pdf_path.name, i, exc)
            raw = ""

        cleaned = " ".join(raw.split())  # normaliza espacios/saltos de línea
        if cleaned:
            pages.append(PageText(source=pdf_path.name, page_number=i, text=cleaned))

    return pages


def load_documents(folder: str | Path) -> list[PageText]:
    """Extrae el texto de todos los PDFs de una carpeta."""
    all_pages: list[PageText] = []
    for pdf_path in list_pdf_files(folder):
        pages = extract_pages(pdf_path)
        if not pages:
            logger.info("Sin texto extraíble en %s (¿escaneado sin OCR?)", pdf_path.name)
        all_pages.extend(pages)
    return all_pages
