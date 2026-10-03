from vision.management.commands.sync_workers import sincronizar, unidad


class ExecutorFalso:
    def __init__(self, corriendo=()):
        self._corriendo = set(corriendo)
        self.arrancadas = []
        self.paradas = []

    def activas(self):
        return set(self._corriendo)

    def arrancar(self, unit):
        self.arrancadas.append(unit)
        self._corriendo.add(unit)

    def parar(self, unit):
        self.paradas.append(unit)
        self._corriendo.discard(unit)


def test_arranca_las_habilitadas_que_no_corren():
    ex = ExecutorFalso()
    sincronizar([3, 5], ex)
    assert set(ex.arrancadas) == {unidad(3), unidad(5)}
    assert ex.paradas == []


def test_para_las_que_ya_no_estan_habilitadas():
    ex = ExecutorFalso(corriendo=[unidad(3), unidad(9)])
    sincronizar([3], ex)
    assert ex.arrancadas == []
    assert ex.paradas == [unidad(9)]


def test_es_idempotente():
    ex = ExecutorFalso()
    sincronizar([3, 5], ex)
    ex.arrancadas.clear()
    ex.paradas.clear()

    sincronizar([3, 5], ex)   # segunda corrida, mismo estado deseado

    assert ex.arrancadas == []
    assert ex.paradas == []
