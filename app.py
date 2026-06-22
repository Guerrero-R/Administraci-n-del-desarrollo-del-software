"""
SmartStudy AI - Punto de entrada.

Toda la interfaz (estilos, animaciones, flujo de 3 pasos y componentes) vive
en `app/ui.py`. Aqui solo cargamos la configuracion del entorno y lanzamos la
UI: no se pierde ninguna funcionalidad de los Sprints (HU-01 a HU-07).

Ejecutar con:  streamlit run app.py
"""

import os

from dotenv import load_dotenv

from app.ui import render_app

load_dotenv()

MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "10"))

render_app(MAX_FILE_MB)