MAX_RESUMEN_DIAS = 30

from tenancy.rubros import RUBROS


def resumen_diario_no_duplicado(fecha, rubro_clave):
    return {
        "fecha": str(fecha),
        "rubro": rubro_clave,
        "metrica_principal": RUBROS.get(rubro_clave, {}).get("metrica_principal", ""),
    }

def generar_resumen_diario(rubro_clave):
    rubro = RUBROS.get(rubro_clave)
    if not rubro:
        return None
    # El valor mínimo: un número sintético que representa la métrica
    # En una ronda futura se conectará con Recorrido.pistas; esta ronda solo define el contrato.
    valor = rubro.get("umbral_default", 0)
    return {
        "metrica_principal": rubro["metrica_principal"],
        "valor": valor,
        "rubro": rubro_clave,
    }
