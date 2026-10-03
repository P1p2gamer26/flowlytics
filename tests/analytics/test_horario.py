# tests/analytics/test_horario.py
"""Cuándo está abierto el local, en su propia zona horaria.

Sin base de datos a propósito: `en_horario` solo lee tres atributos, así que un
`SimpleNamespace` basta y el test corre en milisegundos.
"""
from datetime import datetime, time, timezone as dt_tz
from types import SimpleNamespace

from analytics.horario import en_horario


def negocio(abre, cierra, zona="America/Bogota"):
    return SimpleNamespace(abre=abre, cierra=cierra, timezone=zona)


def utc(hora, minuto=0):
    return datetime(2026, 9, 9, hora, minuto, tzinfo=dt_tz.utc)


def test_dentro_del_horario_se_avisa():
    # 15:00 UTC son las 10:00 en Bogotá: el local lleva dos horas abierto.
    assert en_horario(negocio(time(8), time(20)), utc(15)) is True


def test_de_madrugada_no_se_avisa():
    # 08:00 UTC son las 03:00 en Bogotá. Este es el bug que cierra la fase.
    assert en_horario(negocio(time(8), time(20)), utc(8)) is False


def test_justo_al_abrir_ya_se_avisa_y_justo_al_cerrar_ya_no():
    tienda = negocio(time(8), time(20))
    assert en_horario(tienda, utc(13)) is True    # 08:00 en Bogotá
    assert en_horario(tienda, utc(1)) is False    # 20:00 en Bogotá


def test_un_bar_que_cierra_de_madrugada_sigue_abierto_a_la_una():
    bar = negocio(time(18), time(2))
    assert en_horario(bar, utc(6)) is True        # 01:00 en Bogotá
    assert en_horario(bar, utc(20)) is False      # 15:00 en Bogotá


def test_sin_horario_configurado_se_avisa_a_cualquier_hora():
    # Es el valor por defecto: nadie pierde un aviso por no haber llenado un
    # campo que no sabía que existía.
    assert en_horario(negocio(time(0), time(0)), utc(8)) is True


def test_una_zona_horaria_mal_escrita_no_se_come_el_aviso():
    # Ante la duda se avisa: un aviso de más molesta, uno de menos cuesta una
    # fila sin atender.
    raro = negocio(time(0, 1), time(23, 59), zona="Marte/Olympus")
    assert en_horario(raro, utc(12)) is True
