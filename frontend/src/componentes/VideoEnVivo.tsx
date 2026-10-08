import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { get } from "../api";
import { CapaCalor } from "./CapaCalor";
import { estela } from "./Rastros";

type Zona = { id: number; name: string; kind: string; polygon: [number, number][] };
export type Capa = "normal" | "calor" | "rutas" | "zonas" | "personas";
export const CAPAS: Capa[] = ["normal", "calor", "rutas", "zonas", "personas"];

export type CamaraEnVivo = {
  id: number; name: string; negocio: string; negocio_id: number;
  tipo: "youtube" | "archivo" | "stream"; youtube_id: string | null; video: string | null;
  width: number; height: number; viva: boolean; gente_ahora: number; zonas: Zona[];
};

type Calor = { grid: number[][]; cols: number; rows: number };
type Trayectoria = { track_id: number; points: [number, number][]; started_at: string; ended_at: string };

// Canvas no entiende var(--...): color propio, visible sobre video.
const COLOR_ESTELA = "#ffd23f";
const ETIQUETA: Record<Capa, string> = { normal: "Normal", calor: "Calor", rutas: "Rutas", zonas: "Zonas", personas: "Personas" };

export function VideoEnVivo({ camara, capaGlobal }: { camara: CamaraEnVivo; capaGlobal: Capa }) {
  const { id, name, negocio, tipo, youtube_id, video, viva, gente_ahora, zonas } = camara;
  const [capa, setCapa] = useState<Capa>(capaGlobal);
  const [calor, setCalor] = useState<Calor | null>(null);
  const [trayectorias, setTrayectorias] = useState<Trayectoria[]>([]);
  const [tick, setTick] = useState(0);
  const canvasRutasRef = useRef<HTMLCanvasElement>(null);
  const w = camara.width || 1280;
  const h = camara.height || 720;

  useEffect(() => setCapa(capaGlobal), [capaGlobal]);

  useEffect(() => {
    if (capa !== "personas") return;
    const reloj = setInterval(() => setTick(t => t + 1), 2000);
    return () => clearInterval(reloj);
  }, [capa]);

  useEffect(() => {
    if (capa !== "calor" && capa !== "rutas") return;
    const cargar = async () => {
      if (capa === "calor") {
        const hoy = new Date().toLocaleDateString("en-CA");
        const ayer = new Date(Date.now() - 86400000).toLocaleDateString("en-CA");
        try {
          const r = await get<Calor>(`/api/camaras/${id}/mapa_calor/?desde=${ayer}&hasta=${hoy}`);
          setCalor(r.grid.length ? r : null);
        } catch {
          setCalor(null);
        }
      } else {
        try {
          const r = await get<{ recorridos: Trayectoria[] }>(`/api/camaras/${id}/trayectorias/?segundos=90&puntos=6`);
          setTrayectorias(r.recorridos);
        } catch {
          setTrayectorias([]);
        }
      }
    };
    cargar();
    const intervalMs = capa === "rutas" ? 2000 : 30000;
    const reloj = setInterval(cargar, intervalMs);
    return () => clearInterval(reloj);
  }, [capa, id]);

  useEffect(() => {
    const canvas = canvasRutasRef.current;
    if (!canvas || capa !== "rutas") return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = w;
    canvas.height = h;
    ctx.clearRect(0, 0, w, h);

    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    for (const t of trayectorias) {
      // Los puntos no llevan tiempo y se guardan al cerrar cada ventana (~60 s):
      // por eso se recortan a los últimos 6 (~3 s a ~2 fps) en vez de filtrar por timestamp.
      const segmentos = estela(t.points, 6);
      ctx.strokeStyle = COLOR_ESTELA;
      for (const s of segmentos) {
        ctx.lineWidth = s.grosor;
        ctx.globalAlpha = s.opacidad;
        ctx.beginPath();
        ctx.moveTo(s.desde[0], s.desde[1]);
        ctx.lineTo(s.hasta[0], s.hasta[1]);
        ctx.stroke();
      }
      if (t.points.length > 0) {
        const cabeza = t.points[t.points.length - 1];
        ctx.globalAlpha = 1;
        ctx.lineWidth = 2;
        ctx.strokeStyle = "white";
        ctx.fillStyle = COLOR_ESTELA;
        ctx.beginPath();
        ctx.arc(cabeza[0], cabeza[1], 6, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
    }
  }, [trayectorias, capa, w, h]);

  return (
    <div className="overflow-hidden rounded border border-tinta-2/15 bg-noche">
      <div className="relative w-full" style={{ aspectRatio: `${w} / ${h}` }}>
        {tipo === "youtube" && youtube_id && (
          <iframe title={name} allow="autoplay; encrypted-media"
                  referrerPolicy="strict-origin-when-cross-origin"
                  src={`https://www.youtube.com/embed/${youtube_id}?autoplay=1&mute=1&controls=0&playsinline=1&rel=0`}
                  className="pointer-events-none absolute inset-0 h-full w-full" />
        )}
        {tipo === "archivo" && video && (
          <video src={video} loop muted autoPlay playsInline
                 className="absolute inset-0 h-full w-full object-fill" />
        )}
        {tipo === "stream" && (
          <p className="absolute inset-0 flex items-center justify-center text-sm text-papel/70">
            Esta cámara se analiza, pero su video no se puede mostrar en el navegador.
          </p>
        )}
        {capa === "personas" && (
          <img
            src={`/api/camaras/${id}/ahora/?t=${tick}`}
            alt="Detecciones en vivo"
            className="absolute inset-0 h-full w-full object-fill"
            onError={() => {}}
          />
        )}
        {capa === "calor" && calor && (
          <CapaCalor
            grid={calor.grid}
            cols={calor.cols}
            rows={calor.rows}
            ancho={w}
            alto={h}
            opacidad={0.7}
          />
        )}
        {capa === "rutas" && (
          <canvas
            ref={canvasRutasRef}
            className="pointer-events-none absolute inset-0 h-full w-full"
            aria-hidden="true"
            width={w}
            height={h}
          />
        )}
        <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" aria-hidden="true"
             className="pointer-events-none absolute inset-0 h-full w-full">
          {capa === "zonas" && zonas.map((z) => (
            <g key={z.id}>
              <polygon points={z.polygon.map((p) => p.join(",")).join(" ")} fill="var(--color-zona)"
                       fillOpacity="0.15" stroke="var(--color-zona)" strokeWidth="3" />
              <text x={z.polygon[0][0] + 6} y={z.polygon[0][1] + 22} fill="white" fontSize="22"
                    fontWeight="bold">{z.name}</text>
            </g>
          ))}
        </svg>
        {capa === "personas" && !viva && (
          <p className="absolute inset-0 flex items-center justify-center text-sm text-papel/70 bg-noche/80">
            El detector todavía no ha mandado imagen
          </p>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 px-2 py-1.5 text-sm text-papel">
        <span className="font-medium">{name}</span>
        <span className="text-papel/60">{negocio}</span>
        <span className={`ml-auto ${viva ? "" : "font-semibold text-fila-2"}`}>
          {viva ? `${gente_ahora} persona${gente_ahora === 1 ? "" : "s"}` : "Sin señal"}
        </span>
        <div className="flex overflow-hidden rounded border border-papel/30" role="group" aria-label="Capa">
          {CAPAS.map((c) => (
            <button key={c} type="button" onClick={() => setCapa(c)} aria-pressed={capa === c}
                    className={`px-2 py-0.5 text-xs ${capa === c ? "bg-zona text-white" : "text-papel/80"}`}>
              {ETIQUETA[c]}
            </button>
          ))}
        </div>
        <Link to={`/camaras/${id}/`} className="text-xs text-papel/80 underline">Detalle</Link>
      </div>
      {capa === "calor" && !calor && <p className="px-2 pb-2 text-xs text-papel/60">Sin datos de calor en las últimas 24 h</p>}
    </div>
  );
}