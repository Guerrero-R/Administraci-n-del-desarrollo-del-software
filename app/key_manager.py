"""
Gestion de la API Key.

Centraliza todo lo relacionado con la clave en un solo lugar:
- leerla (de variables de entorno / .env)
- saber si ya esta configurada
- enmascararla para mostrarla sin exponerla
- guardarla / actualizarla en .env (y dejarla activa en el proceso actual)
- una validacion suave del formato
- quitarla

Asi `gemini_service.py` solo recibe la clave ya resuelta y `app/ui.py` puede
mostrar un estado amigable: configurada / sin configurar / cambiar.

IMPORTANTE (seguridad):
Guardar la clave en .env desde la interfaz es adecuado para una app LOCAL de un
solo usuario, como este proyecto. En un despliegue COMPARTIDO no se debe
escribir el .env del servidor (la clave de un usuario quedaria para todos);
alli conviene usar `st.secrets` o las variables de entorno del hosting.
"""

import os

from dotenv import find_dotenv, load_dotenv, set_key, unset_key

# Variables que se consideran validas como clave (orden de prioridad).
ENV_VARS = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
# Variable en la que escribimos cuando el usuario guarda desde la UI.
PRIMARY_VAR = "GEMINI_API_KEY"


def _dotenv_path() -> str:
    """Ruta al archivo .env. Si no existe, apunta a uno en el directorio actual."""
    path = find_dotenv(usecwd=True)
    return path or os.path.join(os.getcwd(), ".env")


def get_api_key() -> str | None:
    """Devuelve la clave actual (sin espacios) o None si no hay ninguna."""
    for var in ENV_VARS:
        value = os.getenv(var)
        if value and value.strip():
            return value.strip()
    return None


def is_configured() -> bool:
    """True si ya hay una clave disponible."""
    return get_api_key() is not None


def mask_key(key: str) -> str:
    """Enmascara la clave para mostrarla en pantalla: 'AIzaSy…aB3d'."""
    key = (key or "").strip()
    if len(key) <= 10:
        return "****"
    return f"{key[:6]}…{key[-4:]}"


def validate_format(key: str) -> tuple[bool, str]:
    """
    Validacion *suave* del formato. Devuelve (es_aceptable, mensaje).

    Solo bloquea entradas claramente invalidas (vacia o con espacios). Para el
    resto devuelve True con un aviso orientativo, porque el formato exacto de
    las claves de Google puede cambiar con el tiempo.
    """
    key = (key or "").strip()
    if not key:
        return False, "La clave esta vacia."
    if any(c.isspace() for c in key):
        return False, "La clave no deberia contener espacios."
    if not key.startswith("AIza"):
        return (
            True,
            "Las API keys de Gemini suelen empezar con 'AIza'. Verifica que "
            "copiaste una API key (no un token OAuth ni otra credencial).",
        )
    if len(key) < 30:
        return True, "La clave parece mas corta de lo habitual; revisa que este completa."
    return True, "Formato correcto."


def save_api_key(key: str) -> None:
    """
    Guarda o actualiza GEMINI_API_KEY en .env y la deja activa de inmediato en
    el proceso actual (sin necesidad de reiniciar la app).
    """
    key = (key or "").strip()
    if not key:
        raise ValueError("No se puede guardar una clave vacia.")

    path = _dotenv_path()
    # set_key crea el archivo si no existe, pero lo aseguramos por robustez.
    if not os.path.exists(path):
        open(path, "a", encoding="utf-8").close()

    set_key(path, PRIMARY_VAR, key)

    # Disponible ya en esta sesion: actualizamos el entorno y recargamos .env.
    os.environ[PRIMARY_VAR] = key
    load_dotenv(path, override=True)


def clear_api_key() -> None:
    """Elimina GEMINI_API_KEY del .env y del proceso actual."""
    path = _dotenv_path()
    if os.path.exists(path):
        unset_key(path, PRIMARY_VAR)
    os.environ.pop(PRIMARY_VAR, None)