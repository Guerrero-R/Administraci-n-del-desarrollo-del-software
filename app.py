import os
import time

import streamlit as st
from dotenv import load_dotenv

from app.gemini_service import GeminiServiceError, generate_study_output
from app.pdf_processor import PDFProcessingError, extract_text_from_pdf
from app.export_utils import build_txt_export, build_json_export

load_dotenv()

MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "10"))

st.set_page_config(page_title="SmartStudy AI", page_icon="📚", layout="wide")

st.title("📚 SmartStudy AI - Sprint 2")
st.caption("MVP con carga de PDF, extraccion de texto, resumen con Gemini y Post-It notes de estudio.")

with st.sidebar:
    st.header("Configuracion")
    summary_style = st.selectbox(
        "Tipo de resumen",
        ["academico", "ejecutivo", "breve", "para estudiar"],
        index=0,
    )
    st.info("Configura GEMINI_API_KEY en tu archivo .env o como variable de entorno.")

uploaded_file = st.file_uploader("Seleccione un archivo PDF", type=["pdf"])

if uploaded_file:
    size_mb = uploaded_file.size / (1024 * 1024)

    if size_mb > MAX_FILE_MB:
        st.error(f"El archivo excede el limite de {MAX_FILE_MB} MB.")
        st.stop()

    st.subheader("HU-01 - Archivo cargado")
    file_col1, file_col2, file_col3 = st.columns(3)
    file_col1.metric("Nombre", uploaded_file.name)
    file_col2.metric("Tamano", f"{size_mb:.2f} MB")
    file_col3.metric("Tipo", uploaded_file.type or "PDF")

    try:
        extraction = extract_text_from_pdf(uploaded_file)
    except PDFProcessingError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Error inesperado al procesar el PDF: {exc}")
        st.stop()

    if not extraction.text:
        st.error("No se detecto texto seleccionable. El PDF podria estar escaneado o vacio.")
        st.stop()

    st.subheader("HU-02 - Texto extraido")
    col1, col2, col3 = st.columns(3)
    col1.metric("Paginas", extraction.pages)
    col2.metric("Palabras", f"{extraction.words:,}")
    col3.metric("Caracteres", f"{extraction.characters:,}")

    with st.expander("Vista previa del texto extraido"):
        st.write(extraction.preview)

    st.subheader("HU-03 - Resumen inteligente con Post-It notes")
    if st.button("Generar resumen y notas de estudio", type="primary"):
        start_time = time.perf_counter()
        try:
            with st.spinner("Generando contenido con Gemini..."):
                output = generate_study_output(extraction.text, summary_style=summary_style)
        except GeminiServiceError as exc:
            st.error(str(exc))
            st.stop()
        except Exception as exc:
            st.error(f"Error inesperado al generar contenido: {exc}")
            st.stop()

        elapsed = time.perf_counter() - start_time
        st.success(f"Contenido generado correctamente en {elapsed:.2f} segundos.")

        st.subheader("HU-04 - Visualizacion del resumen")
        st.text_area("Resumen generado", output.summary, height=260)

        st.download_button(
            "Descargar resumen en TXT",
            data=output.summary,
            file_name="resumen_smartstudy_ai.txt",
            mime="text/plain",
        )

        st.markdown("### 🟨 Ideas clave tipo Post-It")
        idea_cols = st.columns(2)
        for index, idea in enumerate(output.key_ideas):
            with idea_cols[index % 2]:
                st.warning(f"**Idea clave {index + 1}**\n\n{idea}")

        st.markdown("### 🟦 Notas de estudio")
        note_cols = st.columns(2)
        for index, note in enumerate(output.study_notes):
            with note_cols[index % 2]:
                st.info(f"**Nota {index + 1}**\n\n{note}")

        st.markdown("### ✅ Acciones recomendadas")
        for item in output.action_items:
            st.success(item)

        st.subheader("HU-06 - Generación de preguntas de estudio")

        st.markdown("### ❓ Preguntas de estudio")
        if output.study_questions:
            for index, question in enumerate(output.study_questions):
                question_text = question
                answer_text = ""

                if "Respuesta:" in question:
                    parts = question.split("Respuesta:", 1)
                    question_text = parts[0].strip()
                    answer_text = parts[1].strip()

                with st.container(border=True):
                    st.markdown(f"**Pregunta {index + 1}:**")
                    st.write(question_text)

                    if answer_text:
                        st.markdown("**Respuesta:**")
                        st.write(answer_text)
        else:
            st.warning("No se generaron preguntas de estudio para este documento.")

        st.subheader("HU-07 - Flashcards automáticas")

        st.markdown("### 🧠 Flashcards")
        if output.flashcards:
            flashcards_cols = st.columns(2)
            for index, card in enumerate(output.flashcards):
                with flashcards_cols[index %2]:
                    with st.container(border=True):
                        st.markdown(f"***Flashcard {index +1}**")
                        st.markdown(f"***Frente:** {card.front}")
                        st.markdown(f"***Reverso:** {card.back}")
        else:
            st.markdown("No se generaron flashcards para este documento.")
        
        # ──────────────────────────────────────────────
        # HU-08 - Exportación de resultados
        # ──────────────────────────────────────────────
        st.subheader("HU-08 - Exportación de resultados")

        base_name = uploaded_file.name.rsplit(".", 1)[0]

        txt_data = build_txt_export(
            filename=uploaded_file.name,
            summary=output.summary,
            key_ideas=output.key_ideas,
            study_notes=output.study_notes,
            action_items=output.action_items,
            study_questions=output.study_questions,
            flashcards=output.flashcards,
        )

        json_data = build_json_export(
            filename=uploaded_file.name,
            summary=output.summary,
            key_ideas=output.key_ideas,
            study_notes=output.study_notes,
            action_items=output.action_items,
            study_questions=output.study_questions,
            flashcards=output.flashcards,
        )

        st.markdown("Descarga todos los resultados en el formato que prefieras:")

        export_col1, export_col2 = st.columns(2)

        with export_col1:
            st.download_button(
                label="📄 Descargar como TXT",
                data=txt_data,
                file_name=f"{base_name}_smartstudy.txt",
                mime="text/plain",
                use_container_width=True,
            )

        with export_col2:
            st.download_button(
                label="📦 Descargar como JSON",
                data=json_data,
                file_name=f"{base_name}_smartstudy.json",
                mime="application/json",
                use_container_width=True,
            )
else:
    st.info("Carga un PDF para iniciar el flujo del Sprint 1.")

with st.expander("Trazabilidad Sprint 1: HU a funcionalidad"):
    st.table(
        {
            "Historia": ["HU-01", "HU-02", "HU-03", "HU-04", "HU-05", "HU-06", "HU-07", "HU-08"],
            "Mejora aplicada": [
                "Carga PDF con validacion de tamano y metadatos visibles",
                "Extraccion con metricas, paginas, palabras y vista previa",
                "Resumen Gemini + Post-It notes + acciones de estudio",
                "Visualizacion clara, text area y descarga TXT",
                "Errores especificos para PDF invalido, vacio, corrupto o API no configurada",
                "Generación de preguntas de estudio basadas en el contenido del PDF",
                "Generación de flashcards con frente y reverso para repaso rápido",
                "Exportación de resultados en TXT y JSON con todo el contenido generado"
            ],
            "Archivo principal": [
                "app.py",
                "app/pdf_processor.py",
                "app/gemini_service.py",
                "app.py",
                "app.py + app/pdf_processor.py + app/gemini_service.py",
                "app.py + app/gemini_service.py",
                "app.py + app/gemini_service.py",
                "app.py + app/export_utils.py",
            ],
        }
    )
