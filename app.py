"""
Servidor Flask del asistente de preguntas y respuestas sobre PDFs.

Al iniciar, indexa todos los PDFs de documents/. Expone:
  GET  /              -> interfaz de chat
  POST /api/ask        -> {"question": str} -> {"answer": str, "sources": [...]}
  POST /api/reload      -> vuelve a leer documents/ y reconstruye el índice
  GET  /api/status      -> estado del índice (cantidad de documentos/fragmentos)
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from cohere_client import CohereAnswerError, CohereClient
from pdf_loader import list_pdf_files, load_documents
from text_index import TextIndex

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DOCUMENTS_DIR = os.getenv("DOCUMENTS_DIR", "documents")
TOP_K = int(os.getenv("TOP_K", "4"))

app = Flask(__name__)
index = TextIndex()
_cohere_client: CohereClient | None = None


def get_cohere_client() -> CohereClient:
    global _cohere_client
    if _cohere_client is None:
        _cohere_client = CohereClient()
    return _cohere_client


def build_index() -> dict:
    pages = load_documents(DOCUMENTS_DIR)
    n_chunks = index.build(pages)
    n_docs = len(list_pdf_files(DOCUMENTS_DIR))
    logger.info("Índice reconstruido: %d PDF(s), %d fragmento(s)", n_docs, n_chunks)
    return {"documents": n_docs, "chunks": n_chunks}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/status")
def status():
    return jsonify({
        "ready": index.is_ready,
        "documents": len(list_pdf_files(DOCUMENTS_DIR)),
        "chunks": len(index.chunks),
    })


@app.route("/api/reload", methods=["POST"])
def reload_index():
    stats = build_index()
    return jsonify({"ok": True, **stats})


@app.route("/api/ask", methods=["POST"])
def ask():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()

    if not question:
        return jsonify({"error": "Falta el campo 'question'."}), 400

    if not index.is_ready:
        return jsonify({
            "error": "No hay documentos indexados. Agregá PDFs a documents/ y llamá a /api/reload."
        }), 409

    results = index.search(question, top_k=TOP_K)
    fragments = [
        {"source": chunk.source, "page_number": chunk.page_number, "text": chunk.text}
        for chunk, _score in results
    ]

    try:
        client = get_cohere_client()
        answer_text = client.answer(question, fragments)
    except CohereAnswerError as exc:
        logger.error("Error de Cohere: %s", exc)
        return jsonify({"error": str(exc)}), 502

    sources = [
        {"source": f["source"], "page": f["page_number"]}
        for f in fragments
    ]
    return jsonify({"answer": answer_text, "sources": sources})


with app.app_context():
    build_index()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "0") == "1")
