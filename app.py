import os
import time

import streamlit as st
from dotenv import load_dotenv

from app.gemini_service import GeminiServiceError, generate_study_output
from app.pdf_processor import PDFProcessingError, extract_text_from_pdf

load_dotenv()

MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "10"))

st.set_page_config(page_title="SmartStudy AI", page_icon="📚", layout="wide")

st.title("📚 SmartStudy AI - Sprint 1")
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
else:
    st.info("Carga un PDF para iniciar el flujo del Sprint 1.")

with st.expander("Trazabilidad Sprint 1: HU a funcionalidad"):
    st.table(
        {
            "Historia": ["HU-01", "HU-02", "HU-03", "HU-04", "HU-05"],
            "Mejora aplicada": [
                "Carga PDF con validacion de tamano y metadatos visibles",
                "Extraccion con metricas, paginas, palabras y vista previa",
                "Resumen Gemini + Post-It notes + acciones de estudio",
                "Visualizacion clara, text area y descarga TXT",
                "Errores especificos para PDF invalido, vacio, corrupto o API no configurada",
            ],
            "Archivo principal": [
                "app.py",
                "app/pdf_processor.py",
                "app/gemini_service.py",
                "app.py",
                "app.py + app/pdf_processor.py + app/gemini_service.py",
            ],
        }
    )
