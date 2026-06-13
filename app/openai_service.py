import os
from openai import OpenAI

def generate_summary(text):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return "OPENAI_API_KEY no configurada."

    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Genera un resumen claro y breve conservando las ideas principales."
            },
            {
                "role": "user",
                "content": text[:15000]
            }
        ],
        temperature=0.3
    )

    return response.choices[0].message.content
