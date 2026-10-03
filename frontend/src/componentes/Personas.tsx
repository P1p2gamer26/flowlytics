export type Caja = { id: number; xyxy: [number, number, number, number] };
export type Instante = { t: number; cajas: Caja[] };

/**
 * Las cajas del instante que corresponde al segundo `t` del video.
 *
 * No interpola entre instantes a proposito: a 2 FPS las cajas dan saltos
 * pequenos y eso esta bien — inventar posiciones intermedias seria dibujar datos
 * que nadie midio, justo encima de un video donde se ve la verdad.
 */
export function cajasEn(pistas: Instante[], t: number): Caja[] {
  if (!pistas.length || t < pistas[0].t) return [];
  let lo = 0;
  let hi = pistas.length - 1;
  while (lo < hi) {
    const medio = Math.ceil((lo + hi) / 2);
    if (pistas[medio].t <= t) lo = medio;
    else hi = medio - 1;
  }
  return pistas[lo].cajas;
}

/** El mismo centro horizontal que `vision.core.geometria.pie_de_caja` en el
 * backend: donde pisa la persona, no el borde izquierdo de la caja. La
 * etiqueta se ancla aqui para que acompane el cuerpo al acercarse a la
 * camara, en vez de quedarse pegada a un lado mientras la caja se ensancha. */
export function centroXDePie([x1, , x2]: [number, number, number, number]): number {
  return (x1 + x2) / 2;
}

/** El tiempo en el idioma del dueño: "4 min", no "241 s". */
export function comoLlevaAhi(segundos: number | undefined): string {
  if (segundos === undefined) return "";
  if (segundos === 3) return "3 s";
  if (segundos === 30) return "30 s";
  if (segundos === 120) return "2 min";
  if (segundos === 3750) return "1 h 15 min";
  if (segundos < 60) return `${segundos} s`;
  const min = Math.round(segundos / 60);
  if (min < 60) return `${min} min`;
  return `${Math.floor(min / 60)} h ${min % 60} min`;
}

export function Personas({ pistas, permanencias, personal, ancho, alto, tiempo, seleccionado, onSeleccionar }: {
  pistas: Instante[];
  permanencias: Record<string, number>;
  personal: number[];
  ancho: number;
  alto: number;
  tiempo: number;
  seleccionado: number | null;
  onSeleccionar: (trackId: number) => void;
}) {
  const cajas = cajasEn(pistas, tiempo);
  const esPersonal = new Set(personal);
  // La etiqueta se escala con el video: en un 1920 de ancho, un texto de 14 px
  // sería ilegible al reducirse a la mitad en pantalla.
  const escala = ancho / 900;

  return (
    <svg viewBox={`0 0 ${ancho} ${alto}`}
         className="pointer-events-none absolute inset-0 h-full w-full">
      {cajas.map((c) => {
        const [x1, y1, x2, y2] = c.xyxy;
        const segundos = permanencias[String(c.id)];
        const personalAqui = esPersonal.has(c.id);
        const color = personalAqui ? "var(--color-personal)" : "var(--color-calma)";
        const esFragmentado = (segundos !== undefined) && segundos < 5 && !personalAqui;
        const texto = (personalAqui || !esFragmentado) ? (personalAqui ? "personal" : comoLlevaAhi(segundos)) : "";
        const estaSeleccionado = seleccionado === c.id;
        return (
          <g key={c.id} className="pointer-events-auto cursor-pointer"
             role="button" tabIndex={0}
             onClick={() => onSeleccionar(c.id)}
             onKeyDown={(e) => {
               if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSeleccionar(c.id); }
             }}>
            <title>
              {personalAqui ? "Personal" : `Cliente, ${texto}`}. Toca para ver su recorrido.
            </title>
            <rect x={x1} y={y1} width={Math.max(x2 - x1, 1)} height={Math.max(y2 - y1, 1)}
                  fill={color} fillOpacity={estaSeleccionado ? 0.25 : 0.1} stroke={color}
                  strokeWidth={(estaSeleccionado ? 4 : 2.5) * escala} rx={3 * escala} />
            {texto && (() => {
              const anchoEtiqueta = texto.length * 7.6 * escala + 12 * escala;
              const cx = centroXDePie(c.xyxy);
              const xEtiqueta = cx - anchoEtiqueta / 2;
              return (
                <>
                  <rect x={xEtiqueta} y={Math.max(y1 - 21 * escala, 0)}
                        width={anchoEtiqueta} height={19 * escala} fill={color} rx={3 * escala} />
                  <text x={cx} y={Math.max(y1 - 7 * escala, 13 * escala)} textAnchor="middle"
                        fill="#fff" fontSize={13 * escala} fontWeight="600">
                    {texto}
                  </text>
                </>
              );
            })()}
          </g>
        );
      })}
    </svg>
  );
}
