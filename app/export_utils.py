"""
Utilidades de exportación para SmartStudy AI - HU-08
Genera archivos TXT y JSON con todo el contenido generado.
"""

import json
from dataclasses import asdict
from datetime import datetime


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def build_txt_export(
    filename: str,
    summary: str,
    key_ideas: list[str],
    study_notes: list[str],
    action_items: list[str],
    study_questions: list[str],
    flashcards: list,  # list of objects with .front / .back  OR  dicts
) -> str:
    """
    Construye un string TXT con todo el contenido consolidado.
    Listo para pasarle a st.download_button como `data=`.
    """
    sep = "=" * 60
    lines: list[str] = []

    lines += [
        sep,
        "  SMARTSTUDY AI — RESULTADOS DE ESTUDIO",
        f"  Archivo: {filename}",
        f"  Generado: {_timestamp()}",
        sep,
        "",
    ]

    # --- Resumen ---
    lines += ["RESUMEN", "-" * 40, summary.strip(), ""]

    # --- Ideas clave ---
    if key_ideas:
        lines += ["IDEAS CLAVE", "-" * 40]
        for i, idea in enumerate(key_ideas, 1):
            lines.append(f"{i}. {idea.strip()}")
        lines.append("")

    # --- Notas de estudio ---
    if study_notes:
        lines += ["NOTAS DE ESTUDIO", "-" * 40]
        for i, note in enumerate(study_notes, 1):
            lines.append(f"{i}. {note.strip()}")
        lines.append("")

    # --- Acciones recomendadas ---
    if action_items:
        lines += ["ACCIONES RECOMENDADAS", "-" * 40]
        for item in action_items:
            lines.append(f"✔ {item.strip()}")
        lines.append("")

    # --- Preguntas de estudio ---
    if study_questions:
        lines += ["PREGUNTAS DE ESTUDIO", "-" * 40]
        for i, q in enumerate(study_questions, 1):
            lines.append(f"Pregunta {i}:")
            if "Respuesta:" in q:
                parts = q.split("Respuesta:", 1)
                lines.append(f"  {parts[0].strip()}")
                lines.append(f"  Respuesta: {parts[1].strip()}")
            else:
                lines.append(f"  {q.strip()}")
            lines.append("")

    # --- Flashcards ---
    if flashcards:
        lines += ["FLASHCARDS", "-" * 40]
        for i, card in enumerate(flashcards, 1):
            if hasattr(card, "front"):
                front, back = card.front, card.back
            else:
                front, back = card.get("front", ""), card.get("back", "")
            lines.append(f"Flashcard {i}:")
            lines.append(f"  Frente:  {front.strip()}")
            lines.append(f"  Reverso: {back.strip()}")
            lines.append("")

    lines.append(sep)
    return "\n".join(lines)


def build_json_export(
    filename: str,
    summary: str,
    key_ideas: list[str],
    study_notes: list[str],
    action_items: list[str],
    study_questions: list[str],
    flashcards: list,
) -> str:
    """
    Construye un string JSON con todo el contenido estructurado.
    """
    def _card_to_dict(card):
        if hasattr(card, "front"):
            return {"front": card.front, "back": card.back}
        return card

    payload = {
        "metadata": {
            "source_file": filename,
            "exported_at": _timestamp(),
            "app": "SmartStudy AI",
        },
        "summary": summary.strip(),
        "key_ideas": [k.strip() for k in key_ideas],
        "study_notes": [n.strip() for n in study_notes],
        "action_items": [a.strip() for a in action_items],
        "study_questions": [],
        "flashcards": [_card_to_dict(c) for c in flashcards],
    }

    for q in study_questions:
        if "Respuesta:" in q:
            parts = q.split("Respuesta:", 1)
            payload["study_questions"].append(
                {"question": parts[0].strip(), "answer": parts[1].strip()}
            )
        else:
            payload["study_questions"].append({"question": q.strip(), "answer": ""})

    return json.dumps(payload, ensure_ascii=False, indent=2)