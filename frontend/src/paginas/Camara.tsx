import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { Marco } from "../componentes/Marco";
import { MapaCalor } from "../componentes/MapaCalor";
import { borrar, get, pedirPut, post } from "../api";
import { aEscala, normalEntrada } from "../geometria";

type Zona = { id: number; name: string; kind: string; polygon: [number, number][] };
type Linea = { id: number; name: string; puntos: [number, number][]; invertir: boolean };
type ZonaSugerida = { name: string; kind: string };
type Camara = { id: number; name: string; descripcion: string; contexto: string;
                rubro?: { zonas: ZonaSugerida[]; foco: string };
                zones: Zona[]; lines: Linea[] };
type Vista = { image: string; width: number; height: number; video: string | null };
type Progreso = { ventanas: number; eventos: number; viva: boolean;
                  reconexiones: number; ultimo_error: string };
type Recorrido = { track_id: number; points: [number, number][]; started_at: string };
type Recorridos = { recorridos: Recorrido[] };

export default function Camara() {
  const { id } = useParams();
  const [camara, setCamara] = useState<Camara | null>(null);
  const [vista, setVista] = useState<Vista | null>(null);
  const [puntos, setPuntos] = useState<[number, number][]>([]);
  const [nombre, setNombre] = useState("fila");
  // Tipo de la zona que se está dibujando. Vacío = hereda el de la cámara,
  // que es lo que se hacía antes de que el rubro sugiriera nada.
  const [tipo, setTipo] = useState("");
  // Qué se está dibujando. Una línea son 2 puntos; una zona, 3 o más.
  const [modo, setModo] = useState<"zona" | "linea">("zona");
  const [progreso, setProgreso] = useState<Progreso | null>(null);
  const [recorridos, setRecorridos] = useState<Recorrido[]>([]);
  const [mostrarRecorridos, setMostrarRecorridos] = useState(true);
  const [estado, setEstado] = useState("");
  const lienzo = useRef<HTMLCanvasElement>(null);

  // Mapa de calor: por defecto los últimos 7 días, igual que el reporte.
  const hoyLocal = new Date().toLocaleDateString("en-CA");
  const hace7Local = new Date(Date.now() - 6 * 86400000).toLocaleDateString("en-CA");
  const [desdeCalor, setDesdeCalor] = useState(hace7Local);
  const [hastaCalor, setHastaCalor] = useState(hoyLocal);
  const [compararFranjas, setCompararFranjas] = useState(false);

  useEffect(() => {
    get<Camara>(`/api/camaras/${id}/`).then(setCamara);
    get<Vista>(`/api/camaras/${id}/vista/`).then(setVista);
  }, [id]);

  useEffect(() => {
    get<Progreso>(`/api/camaras/${id}/progreso/`).then(setProgreso);
  }, [id]);

  useEffect(() => {
    get<Recorridos>(`/api/camaras/${id}/trayectorias/`)
      .then((d) => setRecorridos(d.recorridos))
      .catch(() => setRecorridos([]));
  }, [id]);

  // Repinta el canvas cada vez que cambian los puntos o las zonas guardadas.
  useEffect(() => {
    const cv = lienzo.current;
    if (!cv || !vista) return;
    const cx = cv.getContext("2d")!;
    cx.clearRect(0, 0, cv.width, cv.height);

    const dibujar = (poly: [number, number][], color: string, etiqueta?: string) => {
      if (poly.length < 2) return;
      cx.beginPath();
      poly.forEach(([x, y], i) => (i ? cx.lineTo(x, y) : cx.moveTo(x, y)));
      cx.closePath();
      cx.strokeStyle = color;
      cx.lineWidth = 2;
      cx.stroke();
      if (etiqueta) {
        cx.fillStyle = color;
        cx.fillText(etiqueta, poly[0][0] + 4, poly[0][1] - 4);
      }
    };

    const dibujarLinea = (
      puntosLinea: [number, number][], invertir: boolean, color: string, etiqueta?: string,
    ) => {
      if (puntosLinea.length < 2) return;
      const [[ax, ay], [bx, by]] = puntosLinea;
      cx.beginPath();
      cx.moveTo(ax, ay);
      cx.lineTo(bx, by);
      cx.strokeStyle = color;
      cx.lineWidth = 3;
      cx.stroke();

      // La flecha sale del medio de la línea hacia el lado por el que se entra.
      const [nx, ny] = normalEntrada(puntosLinea, invertir);
      const mx = (ax + bx) / 2;
      const my = (ay + by) / 2;
      const largo = 34;
      cx.beginPath();
      cx.moveTo(mx, my);
      cx.lineTo(mx + nx * largo, my + ny * largo);
      cx.stroke();
      cx.beginPath();   // punta
      cx.arc(mx + nx * largo, my + ny * largo, 5, 0, Math.PI * 2);
      cx.fillStyle = color;
      cx.fill();
      if (etiqueta) cx.fillText(etiqueta, ax + 4, ay - 6);
    };

    camara?.zones.forEach((z) => dibujar(z.polygon, "#7a5cff", z.name));
    camara?.lines.forEach((l) => dibujarLinea(l.puntos, l.invertir, "#1f9d55", l.name));
    if (mostrarRecorridos) {
      recorridos.forEach((r) => {
        if (r.points.length < 2) return;
        cx.beginPath();
        r.points.forEach(([x, y], i) => (i ? cx.lineTo(x, y) : cx.moveTo(x, y)));
        cx.strokeStyle = "rgba(214, 35, 106, 0.6)";
        cx.lineWidth = 2;
        cx.stroke();
      });
    }
    if (modo === "linea") dibujarLinea(puntos, false, "#d6236a");
    else dibujar(puntos, "#d6236a");
    puntos.forEach(([x, y]) => {
      cx.fillStyle = "#d6236a";
      cx.beginPath();
      cx.arc(x, y, 4, 0, Math.PI * 2);
      cx.fill();
    });
  }, [puntos, camara, vista, modo, recorridos, mostrarRecorridos]);

  function clic(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!vista) return;
    const caja = e.currentTarget.getBoundingClientRect();
    // Se escala aquí y no al guardar: así lo que ves dibujado está en el mismo
    // sistema de coordenadas que las zonas ya guardadas, aunque el canvas se
    // muestre más pequeño que el video.
    const p = aEscala([e.clientX - caja.left, e.clientY - caja.top],
                      { mostrado: [caja.width, caja.height],
                        real: [vista.width, vista.height] });
    // Una línea son exactamente dos puntos: el tercer clic empieza una nueva.
    setPuntos(modo === "linea" && puntos.length >= 2 ? [p] : [...puntos, p]);
  }

  async function guardar() {
    if (!vista) return;
    // Los puntos ya vienen en píxeles del frame desde `clic`: no hay que escalar.
    if (modo === "linea") {
      if (puntos.length !== 2) {
        setEstado("Una línea de entrada son dos clics: uno a cada lado de la puerta.");
        return;
      }
      await post(`/api/camaras/${id}/lineas/`, { name: nombre, puntos });
      setEstado(`Línea "${nombre}" guardada. Si la flecha apunta hacia afuera, ` +
                `usa "Invertir sentido".`);
    } else {
      if (puntos.length < 3) {
        setEstado("Una zona necesita al menos 3 puntos.");
        return;
      }
      await post(`/api/camaras/${id}/zonas/`,
                 { name: nombre, kind: tipo || camara?.contexto || "general",
                   polygon: puntos });
      setEstado(`Zona "${nombre}" guardada.`);
    }
    setPuntos([]);
    setCamara(await get<Camara>(`/api/camaras/${id}/`));
  }

  async function sugerir() {
    setEstado("Analizando el video… (tarda unos segundos)");
    try {
      const s = await get<{ polygon: [number, number][]; muestras: number }>(
        `/api/camaras/${id}/sugerir_zona/`,
      );
      setPuntos(s.polygon);
      setEstado(`Sugerencia con ${s.muestras} detecciones. Ajústala o límpiala.`);
    } catch (e) {
      setEstado((e as Error).message);
    }
  }

  async function analizar() {
    setEstado("Analizando…");
    try {
      await post(`/api/camaras/${id}/procesar/`, { segundos: 60 });
    } catch (e) {
      setEstado((e as Error).message);
      return;
    }
    const reloj = setInterval(async () => {
      const p = await get<Progreso>(`/api/camaras/${id}/progreso/`);
      setProgreso(p);
      if (!p.viva && p.ventanas > 0) {
        clearInterval(reloj);
        setEstado(`Analizado: ${p.ventanas} ventanas, ${p.eventos} eventos.`);
      }
    }, 3000);
  }

  if (!camara || !vista) {
    return <Marco titulo="Cámara"><p className="col-span-12">Cargando…</p></Marco>;
  }

  return (
    <Marco titulo={camara.name}>
      <p className="col-span-12 text-tinta-2">{camara.descripcion}</p>

      <div className="relative col-span-12 inline-block w-fit">
        {vista.video && (
          <video src={vista.video} loop muted playsInline autoPlay
                 className="absolute inset-0 h-full w-full rounded object-cover" />
        )}
        <canvas ref={lienzo} width={vista.width} height={vista.height} onClick={clic}
                className="relative max-w-full cursor-crosshair rounded" />
      </div>

      <div className="col-span-12 flex flex-wrap items-center gap-3">
        <fieldset className="flex items-center gap-3">
          <legend className="sr-only">Qué estás dibujando</legend>
          {(["zona", "linea"] as const).map((m) => (
            <label key={m} className="flex items-center gap-1.5 text-sm">
              <input type="radio" name="modo" value={m} checked={modo === m}
                     onChange={() => { setModo(m); setPuntos([]); }} />
              {m === "zona" ? "Zona (3+ clics)" : "Línea de entrada (2 clics)"}
            </label>
          ))}
        </fieldset>
        {camara.rubro?.zonas.length ? (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-tinta-2">Zonas de tu negocio:</span>
            {camara.rubro.zonas.map((z) => (
<button key={z.name} type="button"
                      onClick={() => { setNombre(z.name); setTipo(z.kind); }}
                      className={`rounded-full px-3 py-1 text-sm ring-1 ring-tinta-2/20 bg-panel ${
                        nombre === z.name ? "ring-zona text-zona" : "ring-tinta-2/20"}`}>
                  {z.name}
                </button>
            ))}
          </div>
        ) : null}
        <label className="text-sm text-tinta-2" htmlFor="nombre-zona">Nombre</label>
        <input id="nombre-zona" value={nombre} onChange={(e) => setNombre(e.target.value)}
               className="rounded-full bg-panel px-4 py-2 ring-1 ring-tinta-2/20" />
        <button onClick={guardar} className="rounded-full bg-marca px-5 py-2.5 font-semibold text-white hover:bg-marca-2">
          Guardar zona
        </button>
        <button onClick={() => setPuntos([])} className="rounded-full bg-panel px-5 py-2.5 font-semibold text-tinta ring-1 ring-tinta-2/20 hover:bg-marca-suave">
          Limpiar
        </button>
        <button onClick={sugerir} className="rounded-full bg-panel px-5 py-2.5 font-semibold text-tinta ring-1 ring-tinta-2/20 hover:bg-marca-suave">
          Sugerir de nuevo
        </button>
        <button onClick={analizar} className="rounded-full bg-marca px-5 py-2.5 font-semibold text-white hover:bg-marca-2">
          Analizar video
        </button>
        {recorridos.length > 0 && (
          <label className="flex items-center gap-2 text-sm text-tinta-2">
            <input type="checkbox" checked={mostrarRecorridos}
                   onChange={(e) => setMostrarRecorridos(e.target.checked)} />
            Mostrar {recorridos.length} recorridos
          </label>
        )}
        <span aria-live="polite" className="text-tinta-2">{estado}</span>
      </div>

      <ul className="col-span-12 space-y-1">
        {camara.zones.map((z) => (
          <li key={z.id} className="flex items-center gap-3 border-t border-tinta-2/15 py-2">
            <span className="h-3 w-3 rounded-sm bg-zona" aria-hidden="true" />
            <span>{z.name}</span>
            <span className="font-mono text-sm text-tinta-2">{z.polygon.length} vértices</span>
            <button className="ml-auto text-alerta"
                    onClick={async () => {
                      await borrar(`/api/zonas/${z.id}/`);
                      setCamara(await get<Camara>(`/api/camaras/${id}/`));
                    }}>
              Borrar
            </button>
          </li>
        ))}
        {!camara.zones.length && (
          <li className="py-6 text-tinta-2">
            Ninguna zona todavía. Haz clic sobre el video para marcar las esquinas
            del área que quieres medir.
          </li>
        )}
      </ul>

      <ul className="col-span-12 space-y-1">
        {camara.lines.map((l) => (
          <li key={l.id} className="flex items-center gap-3 border-t border-tinta-2/15 py-2">
            <span className="h-3 w-3 rounded-sm bg-ok" aria-hidden="true" />
            <span>{l.name}</span>
            <span className="text-sm text-tinta-2">
              línea de entrada{l.invertir ? " (sentido invertido)" : ""}
            </span>
            <button className="ml-auto underline"
                    onClick={async () => {
                      await pedirPut(`/api/lineas/${l.id}/`, { invertir: !l.invertir });
                      setCamara(await get<Camara>(`/api/camaras/${id}/`));
                    }}>
              Invertir sentido
            </button>
            <button className="text-alerta"
                    onClick={async () => {
                      await borrar(`/api/lineas/${l.id}/`);
                      setCamara(await get<Camara>(`/api/camaras/${id}/`));
                    }}>
              Borrar
            </button>
          </li>
        ))}
        {!camara.lines.length && (
          <li className="py-6 text-tinta-2">
            Sin línea de entrada, el panel no puede decir cuánta gente entró. Marca
            dos puntos sobre la puerta, uno a cada lado.
          </li>
        )}
      </ul>

      {progreso && (
        <p className="col-span-12 font-mono text-sm text-tinta-2">
          {progreso.ventanas} ventanas · {progreso.eventos} eventos
          {progreso.reconexiones > 0 && ` · ${progreso.reconexiones} reconexiones`}
          {progreso.ultimo_error && ` · ${progreso.ultimo_error}`}
        </p>
      )}

      <div className="col-span-12 space-y-3 border-t border-tinta-2/15 pt-4">
        <h2 className="font-semibold">Mapa de calor: dónde se para la gente</h2>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm" htmlFor="desde-calor">
            Desde
            <input id="desde-calor" type="date" value={desdeCalor}
                   onChange={(e) => setDesdeCalor(e.target.value)}
                   className="rounded-full bg-panel px-4 py-2 ring-1 ring-tinta-2/20" />
          </label>
          <label className="flex items-center gap-2 text-sm" htmlFor="hasta-calor">
            Hasta
            <input id="hasta-calor" type="date" value={hastaCalor}
                   onChange={(e) => setHastaCalor(e.target.value)}
                   className="rounded-full bg-panel px-4 py-2 ring-1 ring-tinta-2/20" />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={compararFranjas}
                   onChange={(e) => setCompararFranjas(e.target.checked)} />
            Comparar mañana y tarde
          </label>
        </div>
        {compararFranjas ? (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="mb-1 text-sm text-tinta-2">Mañana</p>
              <MapaCalor camaraId={Number(id)} ancho={vista.width} alto={vista.height}
                         imagen={vista.image} zonas={camara.zones} desde={desdeCalor}
                         hasta={hastaCalor} franja="manana" />
            </div>
            <div>
              <p className="mb-1 text-sm text-tinta-2">Tarde</p>
              <MapaCalor camaraId={Number(id)} ancho={vista.width} alto={vista.height}
                         imagen={vista.image} zonas={camara.zones} desde={desdeCalor}
                         hasta={hastaCalor} franja="tarde" />
            </div>
          </div>
        ) : (
          <MapaCalor camaraId={Number(id)} ancho={vista.width} alto={vista.height}
                     imagen={vista.image} zonas={camara.zones} desde={desdeCalor}
                     hasta={hastaCalor} />
        )}
      </div>
    </Marco>
  );
}
