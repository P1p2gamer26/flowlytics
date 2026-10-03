"""Compara lo que mide el sistema contra el conteo de referencia anotado a mano.

Puro: recibe diccionarios de números, no toca video ni base de datos. El comando
reporte_precision reúne los datos reales (corriendo el pipeline sobre cada video)
y llama aquí. Un video sin anotar en la referencia se omite: no se puede medir el
error contra una verdad que no existe.
"""

METRICAS = ["entradas", "salidas", "aforo_max"]


def error_pct(medido, referencia):
    if referencia == 0:
        return 0.0 if medido == 0 else 100.0
    return abs(medido - referencia) / referencia * 100.0


def calcular_error(medido, referencia):
    errores = {}
    for m in METRICAS:
        ref = referencia.get(m)
        if ref is None:
            continue
        errores[m] = error_pct(medido.get(m, 0) or 0, ref)
    return errores


def resumen(resultados):
    acumulado, cuenta = {}, {}
    for r in resultados:
        for metrica, val in r["errores"].items():
            acumulado[metrica] = acumulado.get(metrica, 0.0) + val
            cuenta[metrica] = cuenta.get(metrica, 0) + 1
    return {m: acumulado[m] / cuenta[m] for m in acumulado}


def medir_desde_ventanas(ventanas):
    """Lo que midió una pasada del pipeline, en las tres métricas de METRICAS.

    Recibe WindowSummary (o cualquier objeto con `.crossings` y `.occupancy_max`):
    así se prueba sin abrir un video ni cargar YOLO. Los cruces se suman entre
    ventanas y entre líneas; el aforo es el máximo, no la suma — siete personas
    en una ventana y tres en otra no son diez a la vez.
    """
    entradas = salidas = aforo_max = 0
    for ventana in ventanas:
        for e, s in ventana.crossings.values():
            entradas += e
            salidas += s
        aforo_max = max(aforo_max, max(ventana.occupancy_max.values(), default=0))
    return {"entradas": entradas, "salidas": salidas, "aforo_max": aforo_max}


def _anotado(entry):
    return any(entry.get(m) is not None for m in METRICAS)


# a partir de este error % una fila se cita como caso donde el sistema falla
UMBRAL_FALLA = 15.0


def sin_anotar(referencia):
    """Los videos del banco sin conteo a mano: no se puede medir el error contra
    una verdad que no existe, pero tampoco se pueden esconder."""
    return [e["ruta"] for e in referencia.get("videos", []) if not _anotado(e)]


def generar_reporte(referencia, medidor):
    """referencia: el dict de demo/referencia.json. medidor(entry) -> dict medido.
    Devuelve (texto_markdown, resultados)."""
    videos = referencia.get("videos", [])
    resultados, filas = [], []
    for entry in videos:
        if not _anotado(entry):
            continue
        medido = medidor(entry)
        errores = calcular_error(medido, entry)
        resultados.append({"video": entry["ruta"], "errores": errores})
        filas.append((entry["ruta"], entry, medido, errores))

    lineas = [
        "# Reporte de precisión", "",
        f"Medidos **{len(resultados)} de {len(videos)}** videos del banco: los que "
        "tienen conteo de referencia anotado a mano. La verdad es la anotación "
        "manual; el sistema no se mide contra su propia salida.", "",
        "| Video | Métrica | Referencia | Medido | Diferencia | Error % |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for ruta, ref, medido, errores in filas:
        for metrica, err in errores.items():
            dif = (medido.get(metrica) or 0) - ref.get(metrica)
            lineas.append(f"| {ruta} | {metrica} | {ref.get(metrica)} | "
                          f"{medido.get(metrica)} | {dif:+} | {err:.1f} |")

    prom = resumen(resultados)
    lineas += ["", "## Promedio por métrica"]
    if prom:
        for metrica, err in sorted(prom.items()):
            lineas.append(f"- **{metrica}**: {err:.1f}%")
        lineas += ["", "Es una media simple por video: un clip de dos segundos pesa "
                   "igual que uno de dos minutos. Para leerla bien, mírala junto a "
                   "la columna de diferencia."]
    else:
        lineas.append("- (ningún video anotado: nada que medir)")

    lineas += ["", "## Dónde falla"]
    peores = sorted(((err, ruta, metrica)
                     for ruta, _ref, _medido, errores in filas
                     for metrica, err in errores.items() if err >= UMBRAL_FALLA),
                    reverse=True)
    if peores:
        for err, ruta, metrica in peores:
            lineas.append(f"- `{ruta}` · {metrica}: **{err:.1f}%** de error.")
    elif filas:
        lineas.append(f"- Ninguna métrica supera el {UMBRAL_FALLA:.0f}% de error.")
    else:
        lineas.append("- Nada medido todavía, así que nada que reportar.")

    lineas += ["", "## Sin anotar (omitidos: no hay verdad contra la cual medir)"]
    faltantes = sin_anotar(referencia)
    if faltantes:
        for ruta in faltantes:
            lineas.append(f"- `{ruta}`: falta el conteo a mano en `demo/referencia.json`.")
    else:
        lineas.append("- Ninguno: todo el banco está anotado.")

    return "\n".join(lineas), resultados


# lo que tiene toda entrada del banco aunque nadie la haya anotado todavía
PLANTILLA = {"contexto": "", "origen": "", "notas": "",
             "entradas": None, "salidas": None, "aforo_max": None, "lineas": []}


def anotar(referencia, entry):
    """Inserta o actualiza un video en la referencia, buscándolo por `ruta`.

    Conserva lo que ya tenía y el nuevo entry no trae: reanotar el conteo no
    puede borrar las líneas dibujadas ni las notas. Muta y devuelve el dict.
    """
    videos = referencia.setdefault("videos", [])
    for i, existente in enumerate(videos):
        if existente.get("ruta") == entry["ruta"]:
            videos[i] = {**existente, **entry}
            return referencia
    videos.append({**PLANTILLA, **entry})
    return referencia


MARCA_INICIO = "<!-- precision:inicio -->"
MARCA_FIN = "<!-- precision:fin -->"


def insertar_entre_marcas(documento, contenido):
    """Reemplaza lo que haya entre las marcas del documento.

    Falla si no están: publicar en un documento sin marcas sería escribir la
    tabla en un sitio arbitrario, y un documento técnico corrompido en silencio
    es peor que uno desactualizado.
    """
    ini, fin = documento.find(MARCA_INICIO), documento.find(MARCA_FIN)
    if ini == -1 or fin == -1 or fin < ini:
        raise ValueError(f"El documento no tiene las marcas {MARCA_INICIO} / {MARCA_FIN}.")
    return (documento[:ini + len(MARCA_INICIO)] + "\n\n" + contenido.strip() + "\n\n"
            + documento[fin:])


def cuerpo_para_el_documento(texto_reporte):
    """El reporte, listo para vivir dentro de una sección `##` ajena: sin su H1
    y con los `##` bajados a `###`, para no partir la numeración del documento."""
    lineas = texto_reporte.splitlines()
    if lineas and lineas[0].startswith("# "):
        lineas = lineas[1:]
    return "\n".join("#" + l if l.startswith("## ") else l for l in lineas).strip()
