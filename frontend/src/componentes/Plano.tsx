import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { Personas, type Instante } from "./Personas";
import { Rastros, type Rastro } from "./Rastros";
import { get, post } from "../api";

type Zona = { id: number; name: string; polygon: [number, number][] };
type Recorrido = {
  pistas: Instante[];
  rastros: Rastro[];
  permanencias: Record<string, number>;
  personal: number[];
  analizado: boolean;
};

export function Plano({ imagen, video, ancho, alto, zonas, camaraId }: {
  imagen: string; video?: string | null; ancho: number; alto: number;
  zonas: Zona[]; camaraId?: number;
}) {
  const svg = useRef<SVGSVGElement>(null);
  const vid = useRef<HTMLVideoElement>(null);
  const [tiempo, setTiempo] = useState(0);
  const [recorrido, setRecorrido] = useState<Recorrido | null>(null);
  const [mostrarTodos, setMostrarTodos] = useState(false);
  const [seleccionado, setSeleccionado] = useState<number | null>(null);

  useEffect(() => {
    const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducido || !svg.current) return;
    // Los polígonos se dibujan solos al abrir, sobre el video o el primer frame.
    const trazos = svg.current.querySelectorAll<SVGPolygonElement>("polygon");
    trazos.forEach((t) => {
      const largo = t.getTotalLength?.() ?? 1000;
      gsap.fromTo(t,
        { strokeDasharray: largo, strokeDashoffset: largo, fillOpacity: 0 },
        { strokeDashoffset: 0, fillOpacity: 0.12, duration: 1.1, ease: "power2.out",
          stagger: 0.15 });
    });
  }, [zonas]);

  useEffect(() => {
    if (!camaraId) return;
    setRecorrido(null);
    setMostrarTodos(false);
    setSeleccionado(null);
    get<Recorrido>(`/api/camaras/${camaraId}/recorrido/`).then(setRecorrido).catch(() => {});
  }, [camaraId]);

  // El tiempo del video se sigue con requestAnimationFrame y SOLO mientras
  // reproduce: un setInterval fijo seguiría gastando batería con el video parado,
  // y `timeupdate` del navegador solo dispara ~4 veces por segundo, con lo que las
  // cajas irían a tirones detrás de la gente.
  useEffect(() => {
    const el = vid.current;
    if (!el) return;
    let id = 0;
    const seguir = () => { setTiempo(el.currentTime); id = requestAnimationFrame(seguir); };
    const arrancar = () => { if (!id) id = requestAnimationFrame(seguir); };
    const parar = () => { cancelAnimationFrame(id); id = 0; setTiempo(el.currentTime); };
    el.addEventListener("play", arrancar);
    el.addEventListener("pause", parar);
    el.addEventListener("seeked", parar);
    if (!el.paused) arrancar();
    return () => {
      cancelAnimationFrame(id);
      el.removeEventListener("play", arrancar);
      el.removeEventListener("pause", parar);
      el.removeEventListener("seeked", parar);
    };
  }, [video]);

  const marcar = async (trackId: number) => {
    if (!camaraId || !recorrido) return;
    const yaEs = recorrido.personal.includes(trackId);
    // Se pinta al instante y se confirma con el servidor: esperar la respuesta
    // para mover un color hace que el clic se sienta roto.
    setRecorrido({ ...recorrido,
      personal: yaEs ? recorrido.personal.filter((p) => p !== trackId)
                     : [...recorrido.personal, trackId] });
    const r = await post<{ personal: number[] }>(`/api/camaras/${camaraId}/personal/`,
      { track_id: trackId, es_personal: !yaEs }).catch(() => null);
    if (r) setRecorrido((prev) => prev && { ...prev, personal: r.personal });
  };

  const hayPersonas = !!recorrido?.pistas.length;

  return (
    <figure className="col-span-12">
      <div className="relative">
        {video && !mostrarTodos ? (
          <video ref={vid} src={video} autoPlay loop muted playsInline controls
                 width={ancho} height={alto} className="w-full rounded bg-black" />
        ) : (
          <img src={imagen} alt="" width={ancho} height={alto} className="w-full rounded" />
        )}

        <svg ref={svg} viewBox={`0 0 ${ancho} ${alto}`}
             className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true">
          {zonas.map((z) => (
            <polygon key={z.id} points={z.polygon.map((p) => p.join(",")).join(" ")}
                     fill="var(--color-zona)" fillOpacity="0.12"
                     stroke="var(--color-zona)" strokeWidth="3" />
          ))}
        </svg>

        {recorrido?.rastros.length ? (
          <Rastros rastros={recorrido.rastros} ancho={ancho} alto={alto}
                   tiempo={tiempo} todos={mostrarTodos} trackId={seleccionado} />
        ) : null}

        {hayPersonas && recorrido && (
          <Personas pistas={recorrido.pistas} permanencias={recorrido.permanencias}
                    personal={recorrido.personal} ancho={ancho} alto={alto}
                    tiempo={tiempo} seleccionado={seleccionado} onSeleccionar={setSeleccionado} />
        )}
      </div>

      {recorrido && (
        <figcaption className="mt-2 text-sm text-tinta-2">
          {hayPersonas ? (
            <>
              Toca a una persona para ver solo su recorrido; la marca de personal
              se hace con el botón que aparece tras seleccionarla.
            </>
          ) : recorrido.analizado ? (
            <>El análisis no encontró a nadie en este video.</>
          ) : (
            <>Esta cámara todavía no se ha analizado, así que no hay personas que mostrar.</>
          )}
        </figcaption>
      )}

      {recorrido?.rastros.length ? (
        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-tinta-2">
          <label>
            <input type="checkbox" checked={mostrarTodos}
                   onChange={(e) => setMostrarTodos(e.target.checked)} /> Mostrar todos los recorridos
          </label>
          {seleccionado !== null ? (
            <>
              <span>Viendo solo el recorrido {seleccionado}.</span>
              <button type="button" className="underline" onClick={() => setSeleccionado(null)}>Ver todos</button>
              <button type="button" className="underline" onClick={() => marcar(seleccionado)}>
                {recorrido.personal.includes(seleccionado) ? "Quitar marca de personal" : "Marcar como personal"}
              </button>
            </>
          ) : (
            <span>Toca una persona para ver solo su recorrido.</span>
          )}
        </div>
      ) : null}
    </figure>
  );
}
