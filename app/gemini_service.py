import json
import os
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types


@dataclass
class Flashcard:
    front: str
    back: str


@dataclass
class StudyOutput:
    summary: str
    key_ideas: list[str]
    study_notes: list[str]
    action_items: list[str]
    study_questions: list[str]
    flashcards: list[Flashcard]


class GeminiServiceError(Exception):
    """Raised when Gemini cannot generate the requested response."""


def _mask(api_key: str) -> str:
    """Enmascara la clave para mensajes de error (nunca exponer completa)."""
    api_key = (api_key or "").strip()
    if len(api_key) <= 10:
        return "NO_KEY" if not api_key else "****"
    return f"{api_key[:6]}…{api_key[-4:]}"


def _get_client(api_key: str | None = None) -> genai.Client:
    # Prioridad: clave recibida (desde la UI / key_manager) -> variables de entorno.
    key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise GeminiServiceError(
            "No se encontro GEMINI_API_KEY. Configurala en la barra lateral "
            "o en tu archivo .env antes de generar el resumen."
        )
    return genai.Client(api_key=key)


def _safe_json_loads(raw_text: str) -> dict[str, Any]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiServiceError(
            "Gemini respondio, pero el formato no pudo interpretarse como JSON. Intenta nuevamente."
        ) from exc


def generate_study_output(
    text: str,
    summary_style: str = "academico",
    max_input_chars: int | None = None,
    api_key: str | None = None,
) -> StudyOutput:
    """Generate summary plus post-it style study notes using Gemini.

    api_key: clave a usar. Si es None, se toma de las variables de entorno.
    """
    client = _get_client(api_key)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    limit = max_input_chars or int(os.getenv("MAX_INPUT_CHARS", "18000"))
    source_text = text[:limit]

    prompt = f"""
Eres SmartStudy AI, un asistente de estudio para estudiantes universitarios.
Analiza el texto del documento y genera una respuesta estrictamente en JSON valido.
No uses Markdown fuera del JSON.

Estilo de resumen solicitado: {summary_style}

Devuelve exactamente estas claves:
- summary: string con un resumen claro y util para estudiar.
- key_ideas: array de 4 a 6 strings, cada uno como una idea clave tipo Post-It.
- study_notes: array de 4 a 6 strings, cada uno como una nota breve de estudio tipo Post-It.
- action_items: array de 3 a 5 strings, cada uno como recomendacion accionable para el estudiante.
- study_questions: array de 5 a 8 strings, cada uno como una pregunta de estudio basada en el documento, asi como su respuesra.
- flashcards: array de 5 a 8 objetos JSON. Cada objeto debe tener estas claves:
    -front: string con una pregunta, concepto o termino clave.
    -back: string con la respuesta breve y clara.

Reglas:
- Escribe en espanol.
- Prioriza claridad, utilidad academica y fidelidad al documento.
- No inventes informacion no soportada por el texto.
- Cada Post-It debe ser breve y facil de leer.
- Las preguntas de estudio deben evaluar comprension, conceptos importantes, y relaciones entre ideas.
- Las flashcards deben ser breves, utiles para repaso rapido y fieles al documento.

Texto del documento:
{source_text}
"""

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:
        # Nunca incluimos la API key en el mensaje (solo una pista enmascarada).
        used_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
        raise GeminiServiceError(
            f"Error al llamar a Gemini: {exc} (API key usada: {_mask(used_key)})"
        ) from exc

    if not response.text:
        raise GeminiServiceError("Gemini no devolvio contenido para este documento.")

    data = _safe_json_loads(response.text)

    raw_flashcards = data.get("flashcards", [])

    flashcards = []
    for item in raw_flashcards:
        if isinstance(item, dict):
            front = str(item.get("front", "")).strip()
            back = str(item.get("back", "")).strip()
            if front and back:
                flashcards.append(Flashcard(front=front, back=back))

    return StudyOutput(
        summary=str(data.get("summary", "")).strip(),
        key_ideas=[str(item).strip() for item in data.get("key_ideas", []) if str(item).strip()],
        study_notes=[str(item).strip() for item in data.get("study_notes", []) if str(item).strip()],
        action_items=[str(item).strip() for item in data.get("action_items", []) if str(item).strip()],
        study_questions=[
            str(item).strip()
            for item in data.get("study_questions", [])
            if str(item).strip()
        ],
        flashcards=flashcards,
    )