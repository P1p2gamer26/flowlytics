type Tamanos = { mostrado: [number, number]; real: [number, number] };

/** Un clic ocurre en el canvas tal como se ve; las zonas se guardan en
 *  píxeles del frame original, que es lo que mide el worker. */
export function aEscala(
  [x, y]: [number, number],
  { mostrado, real }: Tamanos,
): [number, number] {
  return [
    Math.round((x * real[0]) / mostrado[0]),
    Math.round((y * real[1]) / mostrado[1]),
  ];
}

/** Vector unitario perpendicular a la línea, apuntando al lado por el que se
 *  ENTRA. La convención no es nuestra: la fija sv.LineZone y está clavada en
 *  `tests/vision/test_lines.py`. `invertir` es la misma bandera del modelo,
 *  para cuando en un local la puerta quedó del otro lado. */
export function normalEntrada(
  [[ax, ay], [bx, by]]: [number, number][],
  invertir = false,
): [number, number] {
  const dx = bx - ax;
  const dy = by - ay;
  const largo = Math.hypot(dx, dy);
  if (!largo) return [0, 0];   // dos clics en el mismo píxel: sin sentido que mostrar
  const signo = invertir ? -1 : 1;
  return [(signo * dy) / largo, (signo * -dx) / largo];
}

