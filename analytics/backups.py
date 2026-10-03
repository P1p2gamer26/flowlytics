"""Política de retención de respaldos: 7 diarios + 4 semanales.

Un respaldo que nunca se restauró no es un respaldo (ver restore_check). Aquí solo
se decide qué borrar; el dump y el restore los hacen los comandos con pg_dump/psql.
"""
from datetime import datetime


def _fecha(nombre):
    marca = nombre.split("backup-")[1].split(".sql")[0]
    return datetime.strptime(marca, "%Y%m%dT%H%M%S")


def elegir_para_borrar(nombres, diarios=7, semanales=4):
    ordenados = sorted(nombres, key=_fecha, reverse=True)
    conservar = set(ordenados[:diarios])

    semanas_vistas = set()
    for n in ordenados[diarios:]:
        semana = _fecha(n).isocalendar()[:2]
        if semana not in semanas_vistas and len(semanas_vistas) < semanales:
            semanas_vistas.add(semana)
            conservar.add(n)

    return [n for n in nombres if n not in conservar]
