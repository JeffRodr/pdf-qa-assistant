"""
Cliente de Cohere para generar respuestas ancladas al contexto recuperado.

Envuelve la llamada al endpoint de chat de Cohere con un system prompt
estricto: la respuesta debe basarse únicamente en los fragmentos de
contexto entregados y decir explícitamente cuando no hay información
suficiente, para evitar alucinaciones.
"""

from __future__ import annotations

import os

import cohere

SYSTEM_PROMPT = (
    "Sos un asistente que responde preguntas únicamente a partir del "
    "CONTEXTO que se te entrega, extraído de documentos PDF. "
    "Reglas estrictas:\n"
    "1. No uses conocimiento externo ni supongas datos que no estén en el CONTEXTO.\n"
    "2. Si el CONTEXTO no alcanza para responder, decí explícitamente que no "
    "encontraste esa información en los documentos cargados.\n"
    "3. Cuando respondas, citá de qué documento y página sale la información "
    "si esos datos están disponibles.\n"
    "4. Respondé en el mismo idioma de la pregunta, de forma clara y concisa."
)


class CohereAnswerError(RuntimeError):
    pass


class CohereClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        api_key = api_key or os.getenv("COHERE_API_KEY")
        if not api_key:
            raise CohereAnswerError(
                "Falta COHERE_API_KEY. Definila en el archivo .env (ver .env.example)."
            )
        self.model = model or os.getenv("COHERE_MODEL", "command-r-08-2024")
        self._client = cohere.ClientV2(api_key=api_key)

    @staticmethod
    def _format_context(fragments: list[dict]) -> str:
        blocks = []
        for i, frag in enumerate(fragments, start=1):
            blocks.append(
                f"[Fragmento {i} - {frag['source']}, página {frag['page_number']}]\n{frag['text']}"
            )
        return "\n\n".join(blocks)

    def answer(self, question: str, fragments: list[dict]) -> str:
        if not fragments:
            return (
                "No encontré información relacionada en los documentos cargados. "
                "Probá reformular la pregunta o verificá que el PDF correspondiente "
                "esté en la carpeta documents/."
            )

        context = self._format_context(fragments)
        user_message = (
            f"CONTEXTO:\n{context}\n\n"
            f"PREGUNTA: {question}\n\n"
            "Respondé siguiendo estrictamente las reglas del sistema."
        )

        try:
            response = self._client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.2,
            )
        except Exception as exc:  # errores de red, rate limit, auth, etc.
            raise CohereAnswerError(f"Error consultando Cohere: {exc}") from exc

        try:
            return response.message.content[0].text.strip()
        except (AttributeError, IndexError) as exc:
            raise CohereAnswerError("Respuesta inesperada de la API de Cohere") from exc
