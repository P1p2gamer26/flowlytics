"""Tests para la función pura `planificar` del comando correr_camaras."""
import pytest

from vision.management.commands.correr_camaras import planificar


def test_planificar_sin_cambios():
    """Si deseadas == vivas, no hay nada que arrancar ni parar."""
    arrancar, parar = planificar({1, 2}, {1: object(), 2: object()})
    assert arrancar == set()
    assert parar == set()


def test_planificar_arrancar_nuevas():
    """Cámaras en deseadas pero no en vivas -> arrancar."""
    arrancar, parar = planificar({1, 2, 3}, {1: object()})
    assert arrancar == {2, 3}
    assert parar == set()


def test_planificar_parar_sobrantes():
    """Cámaras en vivas pero no en deseadas -> parar."""
    arrancar, parar = planificar({1}, {1: object(), 2: object(), 3: object()})
    assert arrancar == set()
    assert parar == {2, 3}


def test_planificar_mezcla():
    """Algunas nuevas, algunas sobrantes."""
    arrancar, parar = planificar({1, 2, 4}, {1: object(), 3: object()})
    assert arrancar == {2, 4}
    assert parar == {3}


def test_planificar_todo_vacio():
    """Sin cámaras deseadas ni vivas."""
    arrancar, parar = planificar(set(), {})
    assert arrancar == set()
    assert parar == set()


def test_planificar_solo_vivas():
    """Solo hay workers vivos, ninguna deseada -> parar todas."""
    arrancar, parar = planificar(set(), {1: object(), 2: object()})
    assert arrancar == set()
    assert parar == {1, 2}


def test_planificar_solo_deseadas():
    """Solo hay cámaras deseadas, ningún worker -> arrancar todas."""
    arrancar, parar = planificar({1, 2, 3}, {})
    assert arrancar == {1, 2, 3}
    assert parar == set()