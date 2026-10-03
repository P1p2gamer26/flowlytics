"""Qué se ve en un frame, en una frase, y a qué contexto corresponde.

Un modelo de lenguaje describiendo una imagen puede contestar cualquier cosa:
todo lo que sale de aquí está acotado a lo que el resto del sistema entiende, y
una respuesta rara degrada a "general" en vez de romper la carga del video.
"""
import json

from cameras.models import CONTEXTOS

PROMPT = """Mira este frame de una cámara de seguridad de un negocio.

Responde SOLO con un objeto JSON, sin texto alrededor, con estas dos claves:
- "descripcion": una frase en español, máximo 20 palabras, que diga qué lugar
  es y qué se ve. Ejemplo: "Pasillo central de un supermercado, con las cajas
  registradoras al fondo."
- "contexto": exactamente uno de estos valores: {valores}.

Si no distingues el lugar, usa "general"."""


def describir_frame(jpeg, llm):
    validos = [v for v, _ in CONTEXTOS]
    crudo = llm.describir_imagen(PROMPT.format(valores=", ".join(validos)), jpeg)
    try:
        datos = json.loads(crudo[crudo.index("{"):crudo.rindex("}") + 1])
    except (ValueError, TypeError):
        return {"descripcion": "", "contexto": "general"}

    contexto = datos.get("contexto")
    return {
        "descripcion": str(datos.get("descripcion") or "")[:300],
        "contexto": contexto if contexto in validos else "general",
    }
