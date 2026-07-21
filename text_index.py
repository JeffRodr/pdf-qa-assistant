"""
Indexado y búsqueda de fragmentos de texto (retrieval).

Trocea el texto extraído de los PDFs en fragmentos ("chunks") con
solapamiento y arma un índice TF-IDF (scikit-learn) para poder buscar,
dada una pregunta, los fragmentos más relevantes por similitud coseno.

Usar TF-IDF en vez de una búsqueda por palabras clave simple da mejores
resultados con preguntas formuladas de forma distinta al texto original,
sin depender de un servicio externo de embeddings.
"""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pdf_loader import PageText

DEFAULT_CHUNK_WORDS = 220
DEFAULT_CHUNK_OVERLAP = 40


@dataclass
class Chunk:
    source: str
    page_number: int
    text: str


class TextIndex:
    """Índice TF-IDF en memoria sobre los fragmentos de los PDFs cargados."""

    def __init__(self, chunk_words: int = DEFAULT_CHUNK_WORDS, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
        self.chunk_words = chunk_words
        self.chunk_overlap = chunk_overlap
        self.chunks: list[Chunk] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None

    @property
    def is_ready(self) -> bool:
        return self._matrix is not None and len(self.chunks) > 0

    def _split_into_chunks(self, page: PageText) -> list[Chunk]:
        words = page.text.split()
        if not words:
            return []

        step = max(self.chunk_words - self.chunk_overlap, 1)
        chunks: list[Chunk] = []
        for start in range(0, len(words), step):
            piece = words[start:start + self.chunk_words]
            if not piece:
                continue
            chunks.append(Chunk(source=page.source, page_number=page.page_number, text=" ".join(piece)))
            if start + self.chunk_words >= len(words):
                break
        return chunks

    def build(self, pages: list[PageText]) -> int:
        """Reconstruye el índice a partir de las páginas extraídas de los PDFs."""
        self.chunks = []
        for page in pages:
            self.chunks.extend(self._split_into_chunks(page))

        if not self.chunks:
            self._vectorizer = None
            self._matrix = None
            return 0

        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, 2),
            min_df=1,
        )
        self._matrix = self._vectorizer.fit_transform(c.text for c in self.chunks)
        return len(self.chunks)

    def search(self, query: str, top_k: int = 4) -> list[tuple[Chunk, float]]:
        """Devuelve los top_k fragmentos más relevantes para la consulta."""
        if not self.is_ready or not query.strip():
            return []

        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix).ravel()
        ranked = sorted(zip(self.chunks, scores), key=lambda pair: pair[1], reverse=True)
        return [(chunk, score) for chunk, score in ranked[:top_k] if score > 0]
