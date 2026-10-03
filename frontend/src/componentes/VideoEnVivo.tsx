import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { get } from "../api";
import { colorDeCalor } from "./MapaCalor";

type Zona = { id: number; name: string; kind: string; polygon: [number, number][] };
export type Capa = "normal" | "calor" | "rutas" | "zonas" | "personas";
export const CAPAS: Capa[] = ["normal", "calor", "rutas", "zonas", "personas"];

export type CamaraEnVivo = {
  id: number; name: string; negocio: string; negocio_id: number;
  tipo: "youtube" | "archivo" | "stream"; youtube_id: string | null; video: string | null;
  width: number; height: number; viva: boolean; gente_ahora: number; zonas: Zona[];
};

type Calor = { grid: number[][]; cols: number; rows: number };

const ETIQUETA: Record<Capa, string> = { normal: "Normal", calor: "Calor", rutas: "Rutas", zonas: "Zonas", personas: "Personas" };

export function VideoEnVivo({ camara, capaGlobal }: { camara: CamaraEnVivo; capaGlobal: Capa }) {
  const { id, name, negocio, tipo, youtube_id, video, viva, gente_ahora, zonas } = camara;
  const [capa, setCapa] = useState<Capa>(capaGlobal);
  const [calor, setCalor] = useState<Calor | null>(null);
  const [rutas, setRutas] = useState<[number, number][][]>([]);
  const [tick, setTick] = useState(0);

  // El selector global manda; cada celda puede cambiarla después.
  useEffect(() => setCapa(capaGlobal), [capaGlobal]);

  // Tick cada 2s para refrescar la capa "personas"
  useEffect(() => {
    if (capa !== "personas") return;
    const reloj = setInterval(() => setTick(t => t + 1), 2000);
    return () => clearInterval(reloj);
  }, [capa]);

  // Carga la capa al elegirla y la refresca cada 30 s: los workers siguen escribiendo.
  useEffect(() => {
    if (capa !== "calor" && capa !== "rutas") return;
    const cargar = () => {
      if (capa === "calor") {
        // Ayer y hoy en fecha local: el servidor agrupa por día UTC y aquí es UTC-5.
        const hoy = new Date().toLocaleDateString("en-CA");
        const ayer = new Date(Date.now() - 86400000).toLocaleDateString("en-CA");
        get<Calor>(`/api/camaras/${id}/mapa_calor/?desde=${ayer}&hasta=${hoy}`)
          .then((r) => setCalor(r.grid.length ? r : null))
          .catch(() => setCalor(null));
      } else {
        get<{ recorridos: { points: [number, number][] }[] }>(`/api/camaras/${id}/trayectorias/?minutos=30`)
          .then((r) => setRutas(r.recorridos.map((t) => t.points).filter((p) => p.length > 1)))
          .catch(() => setRutas([]));
      }
    };
    cargar();
    const reloj = setInterval(cargar, 30_000);
    return () => clearInterval(reloj);
  }, [capa, id]);

  // Coordenadas de zonas, calor y rutas están en píxeles del frame de referencia.
  const w = camara.width || 1280;
  const h = camara.height || 720;

  return (
    <div className="overflow-hidden rounded border border-tinta-2/15 bg-noche">
      <div className="relative w-full" style={{ aspectRatio: `${w} / ${h}` }}>
        {tipo === "youtube" && youtube_id && (
          <iframe title={name} allow="autoplay; encrypted-media"
                  // Sin Referer YouTube responde "Error 153"; Django manda same-origin por defecto.
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
        <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" aria-hidden="true"
             className="pointer-events-none absolute inset-0 h-full w-full">
          {capa === "calor" && calor && calor.grid.map((fila, r) => fila.map((v, c) => (
            <rect key={`${r}-${c}`} x={(c * w) / calor.cols} y={(r * h) / calor.rows}
                  width={w / calor.cols} height={h / calor.rows}
                  fill={colorDeCalor(v)} fillOpacity={v * 0.7} />
          )))}
          {capa === "rutas" && rutas.map((p, i) => (
            <polyline key={i} points={p.map(([x, y]) => `${x},${y}`).join(" ")} fill="none"
                      stroke="var(--color-alerta)" strokeWidth={3} strokeLinecap="round" opacity={0.6} />
          ))}
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
      {capa === "rutas" && !rutas.length && <p className="px-2 pb-2 text-xs text-papel/60">Nadie recorrió la escena en los últimos 30 min.</p>}
    </div>
  );
}
