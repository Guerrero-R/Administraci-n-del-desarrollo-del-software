"""
Capa de interfaz de usuario (UI) para SmartStudy AI.

Aqui vive la ORQUESTACION y la logica de la UI (el flujo de 3 pasos
Cargar -> Generar -> Estudiar). La parte visual se externalizo:
- los estilos viven en  app/assets/css/styles.css
- los fragmentos HTML viven en app/assets/html/*.html
y se cargan con el modulo `templates` en cada funcion que los necesita.

`app.py` solo importa `render_app()` y la ejecuta: la logica de negocio
(extraccion de PDF y llamada a Gemini) sigue intacta, no se pierde ninguna
funcionalidad de los Sprints (HU-01 a HU-07).
"""

import html
import time

import streamlit as st

from app import key_manager, templates
from app.gemini_service import GeminiServiceError, generate_study_output
from app.pdf_processor import PDFProcessingError, extract_text_from_pdf

# Paletas tipo "papel de colores" para las notas Post-It.
PALETTE_IDEAS = ["#ffe066", "#ffd43b", "#ffc078", "#ffa94d"]
PALETTE_NOTES = ["#74c0fc", "#a5d8ff", "#99e9f2", "#66d9e8"]
ROTATIONS = [-2.5, 1.8, -1.2, 2.2, -0.8, 1.4]


# ---------------------------------------------------------------------------
# 1. ESTILOS (se cargan desde app/assets/css/styles.css)
# ---------------------------------------------------------------------------
def inject_styles() -> None:
    """Inyecta la hoja de estilos externa (CSS) en la pagina."""
    css = templates.load_css("styles.css")
    # Concatenamos (no f-string ni .format): el CSS tiene llaves { } literales.
    st.markdown("<style>" + css + "</style>", unsafe_allow_html=True)


def _safe(text: str) -> str:
    """Escapa HTML y conserva los saltos de linea como <br>."""
    return html.escape(str(text)).replace("\n", "<br>")


# ---------------------------------------------------------------------------
# 2. COMPONENTES VISUALES
# ---------------------------------------------------------------------------
def render_header() -> None:
    """Encabezado (hero) desde app/assets/html/hero.html."""
    st.markdown(templates.load_html("hero.html"), unsafe_allow_html=True)


def render_stepper(active: int) -> None:
    """Indicador de 3 pasos. active: 1=Cargar, 2=Generar, 3=Estudiar."""
    steps = [
        ("1", "Cargar PDF", "Sube tu documento"),
        ("2", "Generar", "Resumen con IA"),
        ("3", "Estudiar", "Notas y flashcards"),
    ]
    rendered = ""
    for i, (num, label, hint) in enumerate(steps, start=1):
        state = "done" if i < active else "active" if i == active else ""
        bubble = "✓" if i < active else num
        rendered += templates.render_html(
            "stepper_step.html",
            state=state,
            bubble=bubble,
            label=label,
            hint=hint,
        )
    st.markdown(templates.render_html("stepper.html", steps=rendered), unsafe_allow_html=True)


def _render_key_form(form_key: str, button_label: str) -> None:
    """Formulario para introducir/actualizar la clave y guardarla en .env."""
    with st.form(form_key, clear_on_submit=True):
        new_key = st.text_input(
            "Pega tu GEMINI_API_KEY",
            type="password",
            placeholder="AIza…",
            help="Se guardara en tu archivo .env local y quedara activa al instante.",
        )
        submitted = st.form_submit_button(button_label, use_container_width=True)

    if submitted:
        candidate = (new_key or "").strip()
        ok, msg = key_manager.validate_format(candidate)
        if not ok:
            st.error(msg)
            return
        if msg != "Formato correcto.":
            st.warning(msg)  # aviso suave: igual se guarda
        try:
            key_manager.save_api_key(candidate)
        except Exception as exc:  # noqa: BLE001
            st.error(f"No se pudo guardar la clave: {exc}")
            return
        st.success("✅ Clave guardada en .env y activa. ¡Listo para generar!")
        st.rerun()


def render_api_key_section() -> None:
    """🔑 Estado de la API key: configurada (con opcion a cambiar) o sin configurar."""
    st.markdown("### 🔑 API Key de Gemini")

    if key_manager.is_configured():
        key = key_manager.get_api_key()
        st.success(f"✅ Configurada · `{key_manager.mask_key(key)}`")

        # Aviso persistente si la clave guardada no tiene el formato habitual.
        ok, msg = key_manager.validate_format(key)
        if ok and msg != "Formato correcto.":
            st.caption(f"⚠️ {msg}")

        with st.expander("¿Deseas cambiar la clave?"):
            _render_key_form("api_key_change_form", "Actualizar clave")
            if st.button("🗑️ Quitar clave guardada", use_container_width=True):
                key_manager.clear_api_key()
                st.rerun()
    else:
        st.warning("⚠️ Aún no has configurado tu API key.")
        st.caption("Consigue una gratis en aistudio.google.com/apikey")
        _render_key_form("api_key_new_form", "Guardar clave")


def render_sidebar() -> str:
    """Configuracion. Devuelve el estilo de resumen elegido."""
    with st.sidebar:
        st.markdown("### ⚙️ Configuracion")
        summary_style = st.selectbox(
            "Tipo de resumen",
            ["academico", "ejecutivo", "breve", "para estudiar"],
            index=0,
        )
        st.divider()
        render_api_key_section()
    return summary_style


def render_file_card(uploaded_file, size_mb: float) -> None:
    """HU-01 - Metadatos del archivo cargado."""
    st.markdown("#### 📄 HU-01 · Archivo cargado")
    c1, c2, c3 = st.columns(3)
    c1.metric("Nombre", uploaded_file.name)
    c2.metric("Tamaño", f"{size_mb:.2f} MB")
    c3.metric("Tipo", uploaded_file.type or "PDF")


def render_extraction(extraction) -> None:
    """HU-02 - Metricas del texto extraido y vista previa."""
    st.markdown("#### 🔍 HU-02 · Texto extraido")
    c1, c2, c3 = st.columns(3)
    c1.metric("Páginas", extraction.pages)
    c2.metric("Palabras", f"{extraction.words:,}")
    c3.metric("Caracteres", f"{extraction.characters:,}")
    with st.expander("Vista previa del texto extraido"):
        st.write(extraction.preview)


def _postit_board(items, badge_prefix: str, palette) -> None:
    """Renderiza una lista como tablero de notas Post-It (HU-03)."""
    if not items:
        st.info("No se generaron elementos para esta sección.")
        return
    cards = ""
    for i, text in enumerate(items):
        cards += templates.render_html(
            "postit_card.html",
            color=palette[i % len(palette)],
            rot=ROTATIONS[i % len(ROTATIONS)],
            delay=f"{i * 0.08:.2f}",
            badge=f"{badge_prefix} {i + 1}",
            text=_safe(text),
        )
    st.markdown(templates.render_html("postit_board.html", cards=cards), unsafe_allow_html=True)


def _flashcards(cards) -> None:
    """HU-07 - Flashcards que giran con hover o con foco de teclado."""
    if not cards:
        st.info("No se generaron flashcards para este documento.")
        return
    rendered = ""
    for i, card in enumerate(cards):
        rendered += templates.render_html(
            "flashcard.html",
            delay=f"{i * 0.08:.2f}",
            index=i + 1,
            front=_safe(card.front),
            back=_safe(card.back),
        )
    st.markdown(templates.render_html("flashcards.html", cards=rendered), unsafe_allow_html=True)
    st.markdown(templates.load_html("flip_hint.html"), unsafe_allow_html=True)


def _questions(questions) -> None:
    """HU-06 - Preguntas de estudio (conserva la separacion Pregunta/Respuesta)."""
    if not questions:
        st.info("No se generaron preguntas de estudio para este documento.")
        return
    for i, question in enumerate(questions):
        q_text, a_text = question, ""
        if "Respuesta:" in question:
            parts = question.split("Respuesta:", 1)
            q_text = parts[0].strip()
            a_text = parts[1].strip()
        with st.container(border=True):
            st.markdown(f"**Pregunta {i + 1}:** {q_text}")
            if a_text:
                st.markdown(f"**Respuesta:** {a_text}")


def render_results(output, elapsed: float) -> None:
    """HU-03/04/06/07 - Resultados organizados en pestañas (lógica de 3 clicks)."""
    st.success(f"✨ Contenido generado correctamente en {elapsed:.2f} segundos.")

    tab_resumen, tab_ideas, tab_notas, tab_acciones, tab_preguntas, tab_flash = st.tabs(
        ["📝 Resumen", "🟨 Ideas clave", "🟦 Notas", "✅ Acciones", "❓ Preguntas", "🧠 Flashcards"]
    )

    # HU-04 - Visualizacion del resumen + descarga TXT
    with tab_resumen:
        st.text_area("Resumen generado", output.summary, height=300)
        st.download_button(
            "⬇️ Descargar resumen en TXT",
            data=output.summary,
            file_name="resumen_smartstudy_ai.txt",
            mime="text/plain",
        )

    with tab_ideas:
        _postit_board(output.key_ideas, "IDEA", PALETTE_IDEAS)

    with tab_notas:
        _postit_board(output.study_notes, "NOTA", PALETTE_NOTES)

    with tab_acciones:
        if output.action_items:
            for item in output.action_items:
                st.success(f"✅ {item}")
        else:
            st.info("No se generaron acciones recomendadas.")

    with tab_preguntas:
        _questions(output.study_questions)

    with tab_flash:
        _flashcards(output.flashcards)


def render_traceability() -> None:
    """Tabla de trazabilidad HU -> funcionalidad."""
    with st.expander("📌 Trazabilidad Sprint: HU a funcionalidad"):
        st.table(
            {
                "Historia": ["HU-01", "HU-02", "HU-03", "HU-04", "HU-05", "HU-06", "HU-07"],
                "Mejora aplicada": [
                    "Carga PDF con validacion de tamano y metadatos visibles",
                    "Extraccion con metricas, paginas, palabras y vista previa",
                    "Resumen Gemini + Post-It notes + acciones de estudio",
                    "Visualizacion clara, text area y descarga TXT",
                    "Errores especificos para PDF invalido, vacio, corrupto o API no configurada",
                    "Generacion de preguntas de estudio basadas en el contenido del PDF",
                    "Generacion de flashcards con frente y reverso para repaso rapido",
                ],
                "Archivo principal": [
                    "app.py + app/ui.py",
                    "app/pdf_processor.py",
                    "app/gemini_service.py",
                    "app/ui.py",
                    "app/ui.py + app/pdf_processor.py + app/gemini_service.py",
                    "app/ui.py + app/gemini_service.py",
                    "app/ui.py + app/gemini_service.py",
                ],
            }
        )


# ---------------------------------------------------------------------------
# 3. ORQUESTACION (flujo de 3 pasos)
# ---------------------------------------------------------------------------
def render_app(max_file_mb: int = 10) -> None:
    """Punto de entrada de la UI. Lo unico que necesita llamar app.py."""
    # set_page_config DEBE ser la primera instruccion de Streamlit.
    st.set_page_config(page_title="SmartStudy AI", page_icon="📚", layout="wide")
    inject_styles()
    render_header()

    summary_style = render_sidebar()

    uploaded_file = st.file_uploader("📤 Seleccione un archivo PDF", type=["pdf"])

    # Reservamos el hueco del stepper aqui arriba y lo rellenamos al final,
    # cuando ya sabemos en que paso real esta el usuario.
    stepper_slot = st.empty()

    # ---- Paso 1: sin archivo ----
    if not uploaded_file:
        with stepper_slot.container():
            render_stepper(1)
        st.info("👆 Carga un PDF para iniciar el flujo de estudio.")
        render_traceability()
        return

    size_mb = uploaded_file.size / (1024 * 1024)
    if size_mb > max_file_mb:
        with stepper_slot.container():
            render_stepper(1)
        st.error(f"El archivo excede el limite de {max_file_mb} MB.")
        return

    # Si cambia el archivo, descartamos resultados previos en cache.
    file_id = f"{uploaded_file.name}-{uploaded_file.size}"
    if st.session_state.get("file_id") != file_id:
        st.session_state.pop("output", None)
        st.session_state.pop("elapsed", None)
        st.session_state["file_id"] = file_id

    render_file_card(uploaded_file, size_mb)

    # HU-02 - Extraccion (mismo manejo de errores que la version original)
    try:
        extraction = extract_text_from_pdf(uploaded_file)
    except PDFProcessingError as exc:
        with stepper_slot.container():
            render_stepper(2)
        st.error(str(exc))
        return
    except Exception as exc:  # noqa: BLE001
        with stepper_slot.container():
            render_stepper(2)
        st.error(f"Error inesperado al procesar el PDF: {exc}")
        return

    if not extraction.text:
        with stepper_slot.container():
            render_stepper(2)
        st.error("No se detecto texto seleccionable. El PDF podria estar escaneado o vacio.")
        return

    render_extraction(extraction)

    # ---- Paso 2/3: generacion con Gemini ----
    st.markdown("#### 🧠 HU-03 · Resumen inteligente, preguntas y flashcards")

    configured = key_manager.is_configured()
    if not configured:
        st.info("🔑 Para generar, primero configura tu **API key de Gemini** en la barra lateral (◀).")

    if st.button(
        "🚀 Generar resumen y notas de estudio",
        type="primary",
        disabled=not configured,
    ):
        start = time.perf_counter()
        try:
            with st.spinner("Generando contenido con Gemini…"):
                output = generate_study_output(
                    extraction.text,
                    summary_style=summary_style,
                    api_key=key_manager.get_api_key(),
                )
        except GeminiServiceError as exc:
            with stepper_slot.container():
                render_stepper(2)
            st.error(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            with stepper_slot.container():
                render_stepper(2)
            st.error(f"Error inesperado al generar contenido: {exc}")
            return

        # Guardamos en sesion para que los resultados sobrevivan a los reruns
        # (al cambiar de pestana, mover el sidebar, etc.).
        st.session_state["output"] = output
        st.session_state["elapsed"] = time.perf_counter() - start
        st.balloons()  # pequena animacion de celebracion

    # Mostramos resultados persistidos
    if "output" in st.session_state:
        render_results(st.session_state["output"], st.session_state.get("elapsed", 0.0))
        active_step = 3
    else:
        active_step = 2

    with stepper_slot.container():
        render_stepper(active_step)

    render_traceability()