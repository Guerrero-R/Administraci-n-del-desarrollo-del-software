"""
Cargador de assets de la interfaz (CSS y fragmentos HTML).

Centraliza la lectura de los archivos de `app/assets/` para que `ui.py` solo
pida "dame este fragmento" sin preocuparse por rutas ni por leer disco.

Rendimiento:
Los archivos se cachean en memoria, pero la clave de cache incluye la fecha de
modificacion (mtime). Asi, si editas un .css o .html, el cambio se vuelve a
leer en el siguiente rerun (edicion en caliente) sin pagar lecturas repetidas
cuando el archivo no cambia. Es el principio de "cachear I/O estatico" del
material de Vercel, adaptado a este contexto (Streamlit relee el script en cada
interaccion, no el modulo).

Las rutas se resuelven respecto a ESTE archivo, no al directorio de ejecucion,
para que funcione sin importar desde donde se lance `streamlit run`.
"""

from functools import lru_cache
from pathlib import Path
from string import Template

_ASSETS = Path(__file__).resolve().parent / "assets"
_CSS_DIR = _ASSETS / "css"
_HTML_DIR = _ASSETS / "html"


@lru_cache(maxsize=256)
def _read_cached(path_str: str, _mtime: float) -> str:
    # _mtime forma parte de la clave: si cambia, se relee automaticamente.
    return Path(path_str).read_text(encoding="utf-8")


def _read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"No se encontro el asset: {path}")
    return _read_cached(str(path), path.stat().st_mtime)


def load_css(name: str = "styles.css") -> str:
    """Devuelve el contenido de un .css de app/assets/css (texto plano)."""
    return _read(_CSS_DIR / name)


def load_html(name: str) -> str:
    """Devuelve un fragmento HTML estatico de app/assets/html (sin sustitucion)."""
    return _read(_HTML_DIR / name)


def render_html(name: str, **context: object) -> str:
    """
    Devuelve un fragmento HTML sustituyendo los $marcadores por `context`.

    Usa string.Template, asi que los valores que se inyectan pueden contener
    '{', '}' o '$' sin romper nada (solo se procesan los $ del propio fragmento).
    """
    template = Template(_read(_HTML_DIR / name))
    return template.substitute(**context)