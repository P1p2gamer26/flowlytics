# cameras/diagnostico.py
"""Por qué no conecta una cámara, dicho en español.

OpenCV no explica sus fallos: `VideoCapture` devuelve el mismo False si la URL
está mal escrita, si la cámara está apagada, si la contraseña es otra o si el
códec no se decodifica. Aquí esos casos se separan con lo único observable desde
fuera —la forma de la dirección, si el puerto responde, si el stream abre y si
llega un frame— y cada uno se traduce a una frase con la que alguien pueda hacer
algo.

`sondear` y `abrir` se inyectan: los tests no tocan la red. El mensaje NUNCA
incluye la dirección completa, porque puede llevar credenciales.
"""
from urllib.parse import urlparse

PUERTO_POR_ESQUEMA = {"rtsp": 554, "rtsps": 322, "http": 80, "https": 443}


def revisar_direccion(source):
    """Lo que se sabe sin tocar la red. None si la dirección tiene buena pinta."""
    texto = (source or "").strip()
    if not texto:
        return ("Escribe la dirección de la cámara. Suele parecerse a "
                "rtsp://192.168.1.50:554/stream1 y viene en su manual.")
    partes = urlparse(texto)
    if partes.scheme not in PUERTO_POR_ESQUEMA:
        return ("La dirección tiene que empezar por rtsp:// (o http://). "
                "El fabricante de la cámara publica cuál es la suya.")
    if not partes.hostname:
        return "Falta la IP de la cámara después de rtsp://, algo como rtsp://192.168.1.50/…"
    if "@" in partes.netloc:
        return ("No pongas el usuario y la contraseña dentro de la dirección: "
                "van en sus propias casillas, y así se guardan cifradas.")
    return None


def destino(source):
    """(host, puerto) de la dirección, con el puerto por defecto de su esquema."""
    partes = urlparse(source)
    return partes.hostname, partes.port or PUERTO_POR_ESQUEMA[partes.scheme]


def diagnosticar(source, sondear, abrir):
    """{"ok": bool, "mensaje": str}. En orden de coste: forma, puerto, stream, frame.

    Cada escalón solo se sube si el anterior pasó: una dirección mal escrita no
    merece una espera de red, y un equipo que no responde no merece a FFmpeg.
    """
    problema = revisar_direccion(source)
    if problema:
        return {"ok": False, "mensaje": problema}

    host, puerto = destino(source)
    if not sondear(host, puerto):
        return {"ok": False, "mensaje": (
            f"No responde nadie en {host}:{puerto}. Suele ser que la cámara está "
            "apagada, que le cambió la IP, o que este servidor no está en la misma "
            "red que ella.")}

    captura = None
    try:
        captura = abrir()
        if captura is None or not captura.isOpened():
            return {"ok": False, "mensaje": (
                f"El equipo de {host} responde, pero no entrega video. Casi siempre es "
                "el usuario o la contraseña, o que la ruta del stream no es esa: "
                "compruébalos en la configuración de la cámara.")}
        ok, _ = captura.read()
        if not ok:
            return {"ok": False, "mensaje": (
                "Conecta, pero no llega ninguna imagen. Pasa cuando la cámara emite en "
                "H.265: cambia ese stream a H.264 en su configuración.")}
    except Exception:
        # El texto de la excepción de FFmpeg puede traer la URL con contraseña
        # dentro: no se enseña, se traduce.
        return {"ok": False, "mensaje": (
            f"No se pudo abrir el video de {host}. Comprueba la dirección exacta del "
            "stream y el usuario y la contraseña.")}
    finally:
        if captura is not None:
            try:
                captura.release()
            except Exception:
                pass
    return {"ok": True, "mensaje": f"Conectada: está llegando video de {host}."}