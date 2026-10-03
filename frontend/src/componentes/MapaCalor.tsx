import { useEffect, useState } from "react";
import { get } from "../api";

type Zona = { id: number; name: string; polygon: [number, number][] };
type MapaCalorRespuesta = { grid: number[][]; cols: number; rows: number;
                            personas: number; mensaje: string };

// Los tres colores de la escala del sistema, hardcodeados a propósito:
// coinciden con --color-calma / --color-lleno / --color-fila de estilos.css.
// Si esos tres cambian, este archivo también — leer `getComputedStyle` no es
// testeable sin DOM y el test tiene que correr en Node puro.
const CALMA: [number, number, number] = [0x0f, 0x7a, 0x57];
const LLENO: [number, number, number] = [0xe9, 0xa1, 0x3b];
const FILA: [number, number, number] = [0xd6, 0x43, 0x2c];

function mezclar(a: [number, number, number], b: [number, number, number], t: number): string {
  const r = Math.round(a[0] + (b[0] - a[0]) * t);
  const g = Math.round(a[1] + (b[1] - a[1]) * t);
  const bl = Math.round(a[2] + (b[2] - a[2]) * t);
  const hex = (n: number) => n.toString(16).padStart(2, "0");
  return `#${hex(r)}${hex(g)}${hex(bl)}`;
}

/** Interpola por tramos entre calma (0), lleno (0.5) y fila (1). */
export function colorDeCalor(valor: number): string {
  const v = Math.min(1, Math.max(0, valor));
  if (v <= 0.5) return mezclar(CALMA, LLENO, v / 0.5);
  return mezclar(LLENO, FILA, (v - 0.5) / 0.5);
}

export function MapaCalor({ camaraId, ancho, alto, imagen, zonas, desde, hasta, franja }: {
  camaraId: number; ancho: number; alto: number; imagen: string; zonas: Zona[];
  desde?: string; hasta?: string; franja?: "manana" | "tarde";
}) {
  const [datos, setDatos] = useState<MapaCalorRespuesta | null>(null);

  useEffect(() => {
    setDatos(null);
    const params = new URLSearchParams();
    if (desde) params.set("desde", desde);
    if (hasta) params.set("hasta", hasta);
    if (franja) params.set("franja", franja);
    const qs = params.toString();
    get<MapaCalorRespuesta>(`/api/camaras/${camaraId}/mapa_calor/${qs ? `?${qs}` : ""}`)
      .then(setDatos)
      .catch(() => setDatos(null));
  }, [camaraId, desde, hasta, franja]);

  if (!datos) return null;

  if (datos.mensaje) {
    return <p className="text-sm text-tinta-2">{datos.mensaje}</p>;
  }

  const { grid, cols, rows } = datos;
  const cellW = ancho / cols;
  const cellH = alto / rows;

  return (
    <figure className="relative">
      <img src={imagen} alt="" width={ancho} height={alto} className="w-full rounded" />
      <svg viewBox={`0 0 ${ancho} ${alto}`}
           className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true">
        {grid.map((fila, r) =>
          fila.map((valor, c) => (
            <rect key={`${r}-${c}`} x={c * cellW} y={r * cellH} width={cellW} height={cellH}
                  fill={colorDeCalor(valor)} fillOpacity={valor} />
          )),
        )}
        {zonas.map((z) => (
          <polygon key={z.id} points={z.polygon.map((p) => p.join(",")).join(" ")}
                   fill="var(--color-zona)" fillOpacity="0.12"
                   stroke="var(--color-zona)" strokeWidth="3" />
        ))}
      </svg>
    </figure>
  );
}
