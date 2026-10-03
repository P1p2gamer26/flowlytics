"""Que `pip install -r requirements.txt` alcance para arrancar.

Faltaban gunicorn (el ExecStart de vision-web.service) y matplotlib (que importa
analytics/reportes_views.py al cargar las URLs): una VM limpia instalaba todo el
archivo y aun así no levantaba. Este test recorre los imports reales del código
de aplicación y exige que cada uno venga de una distribución listada.
"""
import ast
import sys
from importlib.metadata import distributions
from pathlib import Path

import pytest
from django.conf import settings

RAIZ = Path(settings.BASE_DIR)
APPS = ["analytics", "cameras", "config", "dashboard", "insights", "tenancy", "vision"]
# módulos que no vienen de pypi: son del propio repo o los aporta el runtime
PROPIOS = set(APPS) | {"tests", "automation", "demo", "manage"}


def _paquetes_de(dist):
    """Top-level packages de una distribución instalada.

    `packages_distributions()` de la stdlib en Python 3.10 solo lee
    top_level.txt, que los wheels modernos (matplotlib, anthropic) ya no
    generan; con eso, paquetes instalados de verdad salen como "faltantes".
    Se infiere igual que RECORD lo describe: carpetas con __init__.py o
    módulos sueltos en la raíz.
    """
    declarado = dist.read_text("top_level.txt")
    if declarado:
        return set(declarado.split())
    paquetes = set()
    for archivo in dist.files or []:
        partes = archivo.parts
        if len(partes) == 1 and partes[0].endswith(".py"):
            paquetes.add(Path(partes[0]).stem)
        elif len(partes) > 1 and partes[-1] == "__init__.py":
            paquetes.add(partes[0])
    return paquetes


def packages_distributions():
    mapa = {}
    for dist in distributions():
        nombre = dist.metadata["Name"]
        for paquete in _paquetes_de(dist):
            mapa.setdefault(paquete, []).append(nombre)
    return mapa


def _modulos_importados():
    modulos = set()
    for app in APPS:
        for archivo in (RAIZ / app).rglob("*.py"):
            arbol = ast.parse(archivo.read_text(encoding="utf-8"))
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.Import):
                    modulos.update(a.name.split(".")[0] for a in nodo.names)
                elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                    modulos.add(nodo.module.split(".")[0])
    return {m for m in modulos
            if m not in sys.stdlib_module_names and m not in PROPIOS}


def test_todo_lo_que_importa_la_app_esta_en_requirements():
    requirements = (RAIZ / "requirements.txt").read_text().lower()
    distribuciones = packages_distributions()

    faltantes = []
    for modulo in sorted(_modulos_importados()):
        dists = distribuciones.get(modulo)
        if dists is None:
            pytest.fail(f"{modulo} ni siquiera está instalado en .venv")
        if not any(d.lower() in requirements for d in dists):
            faltantes.append(f"{modulo} (paquete {dists[0]})")

    assert faltantes == [], f"faltan en requirements.txt: {', '.join(faltantes)}"


def test_gunicorn_esta_listado_porque_la_unit_lo_ejecuta():
    # deploy/systemd/vision-web.service apunta a .venv/bin/gunicorn
    assert "gunicorn" in (RAIZ / "requirements.txt").read_text()
