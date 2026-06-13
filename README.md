# SmartStudy AI - Sprint 1 Mejorado con Gemini

Versión de referencia para implementar el Sprint 1 con las historias de usuario elevadas al siguiente nivel.

## Historias implementadas

| HU | Funcionalidad | Mejora de calidad |
|---|---|---|
| HU-01 | Carga de PDF | Muestra nombre, tamaño, tipo y valida límite de MB |
| HU-02 | Extracción de texto | Muestra páginas, palabras, caracteres y vista previa |
| HU-03 | Resumen con IA | Usa Gemini y genera resumen + Post-It notes de estudio |
| HU-04 | Visualización | Text area legible y descarga del resumen en TXT |
| HU-05 | Manejo de errores | Mensajes específicos para PDF corrupto, vacío, escaneado, archivo grande o API key faltante |

## Instalación local

```bash
pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` y agrega tu API key:

```bash
GEMINI_API_KEY=tu_api_key
```

Ejecuta:

```bash
streamlit run app.py
```

## Docker

```bash
docker build -t smartstudy-ai-gemini .
docker run -p 8501:8501 --env-file .env smartstudy-ai-gemini
```

## API usada

Este proyecto usa el SDK actual de Google Gen AI para Python (`google-genai`) y el modelo configurable `gemini-2.5-flash` por defecto.

## Uso de IA sugerido para documentar

Google. (2026). Gemini API mediante Google Gen AI SDK para Python, utilizado para generación de resúmenes, ideas clave tipo Post-It y notas de estudio a partir del texto extraído de documentos PDF.

OpenAI. (2026). ChatGPT (GPT-5.5 Thinking), utilizado como apoyo para generación de código de referencia, documentación técnica y mejora de historias de usuario.

## Nota importante

Este ZIP es una referencia técnica. El equipo debe revisar, adaptar, probar y documentar los cambios antes de presentarlos como parte del entregable.
