"""Rejilla de calor: donde se para la gente, sin Django ni video.

Todo recibe numeros y devuelve numeros; la persistencia y las fechas viven en
`analytics/mapa_calor.py`. Las celdas se calculan sobre la resolucion DE
REFERENCIA de la camara (el frame con el que se dibujaron las zonas), no sobre
la del frame que llega en cada corrida: si el stream cambia de resolucion,
las celdas siguen apuntando al mismo rincon del local. Es la misma tecnica que
`ZoneSet.from_specs` usa para escalar poligonos.
"""

# Menos personas distintas que esto en el periodo pedido y el mapa no se
# pinta: un puñado de visitas parece "aqui se para la gente" y es solo "aqui
# pasaron cuatro personas un minuto". 30 es una cámara con un día flojo, no un
# número mágico — se documenta y se puede ajustar si la práctica dice otra
# cosa.
UMBRAL_PERSONAS = 30


def rejilla_vacia(cols, rows):
    return [[0] * cols for _ in range(rows)]


class GridAccumulator:
    """Acumula, cuadro a cuadro, en qué celda pisó cada persona."""

    def __init__(self, ref_wh, cell_px=40):
        rw, rh = ref_wh
        self.cols = max(1, round(rw / cell_px))
        self.rows = max(1, round(rh / cell_px))
        self._cell_w = rw / self.cols
        self._cell_h = rh / self.rows
        self._grid = rejilla_vacia(self.cols, self.rows)
        self._personas = set()

    def observe(self, pies_con_id):
        """`pies_con_id`: iterable de `(track_id, (x, y))`, YA escalados a la
        resolución de referencia de esta cámara."""
        for tid, (x, y) in pies_con_id:
            col = min(self.cols - 1, max(0, int(x / self._cell_w)))
            row = min(self.rows - 1, max(0, int(y / self._cell_h)))
            self._grid[row][col] += 1
            self._personas.add(tid)

    def cerrar(self):
        """Cierra la ventana en curso y la reinicia. Devuelve `(grid, personas)`."""
        grid, personas = self._grid, len(self._personas)
        self._grid = rejilla_vacia(self.cols, self.rows)
        self._personas = set()
        return grid, personas


def sumar_grids(ventanas):
    """`ventanas`: lista de `(grid, rows, cols, personas)`. Suma celda a celda
    las que coinciden en tamaño con la primera; descarta el resto — un cambio
    de resolución de referencia entre corridas es raro, pero no puede reventar
    el mapa de las demás ventanas. Devuelve `(grid, personas, descartadas)`.
    """
    if not ventanas:
        return [], 0, 0
    _, rows0, cols0, _ = ventanas[0]
    grid = rejilla_vacia(cols0, rows0)
    personas = 0
    descartadas = 0
    for g, rows, cols, p in ventanas:
        if rows != rows0 or cols != cols0:
            descartadas += 1
            continue
        for r in range(rows0):
            for c in range(cols0):
                grid[r][c] += g[r][c]
        personas += p
    return grid, personas, descartadas


def suavizar(grid):
    """Promedio con los vecinos inmediatos (más el propio). Sin esto, una
    rejilla de 40 px por celda se ve a cuadros: los pies caen en el borde de
    una celda casi tanto como en el centro, y el mapa parece un tablero de
    ajedrez en vez de una mancha de calor."""
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    suave = rejilla_vacia(cols, rows)
    for r in range(rows):
        for c in range(cols):
            vecinos = [
                grid[rr][cc]
                for rr in (r - 1, r, r + 1) for cc in (c - 1, c, c + 1)
                if 0 <= rr < rows and 0 <= cc < cols
            ]
            suave[r][c] = sum(vecinos) / len(vecinos)
    return suave


def normalizar(grid):
    """0..1 sobre el máximo de la rejilla. Una rejilla toda en cero se queda en
    cero: dividir por el máximo de una rejilla vacía sería un
    `ZeroDivisionError`, y "vacío" no es un bug, es una cámara sin gente en el
    periodo pedido."""
    maximo = max((v for fila in grid for v in fila), default=0)
    if maximo == 0:
        return grid
    return [[v / maximo for v in fila] for fila in grid]
