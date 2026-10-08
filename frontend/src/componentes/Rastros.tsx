export type PuntoRastro = { t: number; xy: [number, number] };
export type Rastro = { track_id: number; puntos: PuntoRastro[] };

export function segmentosDeCola(puntos: PuntoRastro[], tiempo: number, segundos = 5) {
  const desde = tiempo - segundos;
  const visibles = puntos.filter((p) => p.t >= desde && p.t <= tiempo);
  return visibles.slice(1).map((p, i) => ({
    desde: visibles[i].xy, hasta: p.xy,
    opacidad: Number(((p.t - desde) / segundos).toFixed(2)),
  }));
}

export function estela(puntos: [number, number][], n = 6): {
  desde: [number, number];
  hasta: [number, number];
  opacidad: number;
  grosor: number;
}[] {
  if (puntos.length < 2) return [];
  const ultimos = puntos.slice(-n);
  return ultimos.slice(1).map((hasta, i) => {
    const desde = ultimos[i];
    const t = (i + 1) / (ultimos.length - 1);
    return {
      desde,
      hasta,
      opacidad: Math.round(t * 100) / 100,
      grosor: Math.round((1 + t * 3) * 100) / 100,
    };
  });
}

export function Rastros({ rastros, ancho, alto, tiempo, todos, trackId }: {
  rastros: Rastro[]; ancho: number; alto: number; tiempo: number;
  todos: boolean; trackId: number | null;
}) {
  const visibles = trackId === null ? rastros : rastros.filter((r) => r.track_id === trackId);
  return <svg viewBox={`0 0 ${ancho} ${alto}`} className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true">
    {visibles.flatMap((r) => {
      const segmentos = todos
        ? r.puntos.slice(1).map((p, i) => ({ desde: r.puntos[i].xy, hasta: p.xy, opacidad: 0.5 }))
        : segmentosDeCola(r.puntos, tiempo);
      return segmentos.map((s, i) => <line key={`${r.track_id}-${i}`} x1={s.desde[0]} y1={s.desde[1]}
        x2={s.hasta[0]} y2={s.hasta[1]} stroke="var(--color-alerta)" strokeWidth="3"
        strokeLinecap="round" opacity={s.opacidad} />);
    })}
  </svg>;
}