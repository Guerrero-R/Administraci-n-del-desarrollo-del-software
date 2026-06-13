import json
import os
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types


@dataclass
class StudyOutput:
    summary: str
    key_ideas: list[str]
    study_notes: list[str]
    action_items: list[str]


class GeminiServiceError(Exception):
    """Raised when Gemini cannot generate the requested response."""


def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise GeminiServiceError(
            "No se encontro GEMINI_API_KEY. Configura la variable de entorno antes de generar el resumen."
        )
    return genai.Client(api_key=api_key)


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
) -> StudyOutput:
    """Generate summary plus post-it style study notes using Gemini."""
    client = _get_client()
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

Reglas:
- Escribe en espanol.
- Prioriza claridad, utilidad academica y fidelidad al documento.
- No inventes informacion no soportada por el texto.
- Cada Post-It debe ser breve y facil de leer.

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
        api_key = os.getenv("GEMINI_API_KEY", "")

        masked_key = (
            f"{api_key[:8]}...{api_key[-4:]}"
            if len(api_key) > 12
            else "NO_KEY"
        )

        raise GeminiServiceError(
            f"Error Gemini: {exc} | API Key: {api_key}"
        ) from exc

    if not response.text:
        raise GeminiServiceError("Gemini no devolvio contenido para este documento.")

    data = _safe_json_loads(response.text)
    return StudyOutput(
        summary=str(data.get("summary", "")).strip(),
        key_ideas=[str(item).strip() for item in data.get("key_ideas", []) if str(item).strip()],
        study_notes=[str(item).strip() for item in data.get("study_notes", []) if str(item).strip()],
        action_items=[str(item).strip() for item in data.get("action_items", []) if str(item).strip()],
    )
