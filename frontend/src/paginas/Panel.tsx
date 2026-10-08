import { useEffect, useState } from "react";
import { Marco } from "../componentes/Marco";
import { Plano } from "../componentes/Plano";
import { CintaDelDia, ResumenEnPalabras } from "../componentes/CintaDelDia";
import { TarjetasKpi } from "../componentes/TarjetasKpi";
import { GraficaHoras } from "../componentes/GraficaHoras";
import { BarrasSemana } from "../componentes/BarrasSemana";
import { RecomendacionesIA } from "../componentes/RecomendacionesIA";
import { generarHorasPromedioDemo, generarSemanaDemo, kpisDelDia,
         recomendacionesParaMostrar } from "../panelDatos";
import { get } from "../api";

type Rubro = {
  kind: string; principal: string; metricas: string[];
  etiquetas: Record<string, string>;
  zonas: { name: string; kind: string }[]; foco: string;
};
type Resumen = {
  business: string; date: string;
  total_visitors: number; peak_occupancy: number;
  peak_hour: number | null; avg_queue_seconds: number | null;
  avg_dwell_seconds: number | null;
  staff_coverage_pct: number | null;
  entradas: number | null; salidas: number | null;
  rubro?: Rubro;
  hourly: { hour: number; occupancy_avg: number; visitors: number }[];
  zones: { zone_name: string; zone_kind: string; occupancy_avg: number;
           dwell_seconds: number; visitors: number }[];
};
type Vista = { image: string; width: number; height: number; video: string | null };
type Camara = { id: number; name: string; descripcion: string; es_video: boolean;
                zones: { id: number; name: string; polygon: [number, number][] }[] };
type Extra = {
  camaras_caidas: { camara: string; ultimo_latido: string; ultimo_error: string }[];
  comparativa: null | Record<string, any>;
  recomendacion: string;
};
type Evento = { id: number; kind: string; camera: string; zone: string;
                value: number; occurred_at: string };
type Negocio = { id: number; nombre: string };

/* El sistema guarda claves; el dueño lee español. Estas tablas son la frontera:
   `long_queue` y `queue` no salen nunca a la pantalla. */
const TIPO_ZONA: Record<string, string> = {
  general: "aforo", queue: "fila", counter: "caja", staff: "personal",
  entrada: "entrada", pasillo: "pasillo", escaleras: "escaleras",
  comidas: "comidas", parqueadero: "parqueadero",
};
const QUE_PASO: Record<string, (v: number, zona: string) => string> = {
  long_queue: (v, z) => `${z}: la espera llegó a ${Math.max(1, Math.round(v / 60))} min`,
  empty_counter: (_v, z) => `${z}: se quedó sin nadie atendiendo`,
  overcrowding: (v, z) => `${z}: llegó a ${Math.round(v)} personas a la vez`,
  crowded_queue: (v, z) => `${z}: se juntaron ${Math.round(v)} personas en la fila`,
};
const METRICAS_COMPARATIVA: Record<string, string> = {
  visitantes: "Visitantes", aforo_pico: "Personas a la vez",
  espera_fila_seg: "Espera en fila", cobertura_personal: "Cobertura de personal",
};

// Fecha local en formato YYYY-MM-DD
const hoyLocal = () => new Date().toLocaleDateString("en-CA");

// Sin rubro (backend viejo, respuesta a medias) el panel sigue mostrando algo
// razonable: las tres cifras de apoyo que ya se mostraban antes de esta fase.
const RUBRO_POR_DEFECTO: Rubro = {
  kind: "other", principal: "peak_occupancy",
  metricas: ["peak_occupancy", "avg_queue_seconds", "staff_coverage_pct"],
  etiquetas: {}, zonas: [], foco: "",
};
export default function Panel({ negocio, negocios, onCambiarNegocio }: {
  negocio: number; negocios: Negocio[]; onCambiarNegocio: (id: number) => void;
}) {
  const [resumen, setResumen] = useState<Resumen | null>(null);
  const [camara, setCamara] = useState<Camara | null>(null);
  const [camaras, setCamaras] = useState<Camara[]>([]);
  const [vista, setVista] = useState<Vista | null>(null);
  const [extra, setExtra] = useState<Extra | null>(null);
  const [eventos, setEventos] = useState<Evento[]>([]);
  const [dia, setDia] = useState("");
  const [verCaidas, setVerCaidas] = useState(false);

  useEffect(() => {
    get<Resumen>(`/api/summary/?business=${negocio}&date=${dia}`).then(setResumen);
    get<Extra>(`/api/panel-extra/?business=${negocio}&date=${dia}`).then(setExtra);
    get<Evento[]>(`/api/events/?business=${negocio}`).then(setEventos);
    get<Camara[]>(`/api/camaras/?business=${negocio}`).then(async (cs) => {
      setCamaras(cs);
      if (!cs.length) return;
      const preferida = cs.find((c) => c.es_video && c.zones.length)
        ?? cs.find((c) => c.es_video) ?? cs[0];
      setCamara(preferida);
      setVista(await get<Vista>(`/api/camaras/${preferida.id}/vista/`).catch(() => null));
    });
  }, [negocio, dia]);

  const cambiarCamara = async (id: number) => {
    const c = camaras.find((x) => x.id === id);
    if (!c) return;
    setCamara(c);
    setVista(await get<Vista>(`/api/camaras/${id}/vista/`).catch(() => null));
  };

  if (!resumen) {
    return (
      <Marco titulo="Panel">
        <p className="col-span-12 text-tinta-2">Cargando el día…</p>
      </Marco>
    );
  }

  const esHoy = !dia || dia === hoyLocal();
  const topeZona = Math.max(...resumen.zones.map((z) => z.visitors), 1);
  const rubro = resumen.rubro ?? RUBRO_POR_DEFECTO;
  const visitasPorHora = Array.from({ length: 24 }, (_, h) =>
    resumen.hourly.find((x) => x.hour === h)?.visitors ?? 0);
  const promedioHoras = generarHorasPromedioDemo(visitasPorHora);
  const semana = generarSemanaDemo(resumen.total_visitors, new Date());
  const kpis = kpisDelDia(resumen, semana[5].total, semana[0].total);

  const acciones = (
    <div className="flex items-center gap-2 text-sm">
      {negocios.length > 1 && (
        <select value={negocio} onChange={(e) => onCambiarNegocio(Number(e.target.value))}
                className="rounded-full ring-1 ring-tinta-2/20 bg-panel px-4 py-2">
          {negocios.map((n) => <option key={n.id} value={n.id}>{n.nombre}</option>)}
        </select>
      )}
      <input type="date" value={dia} onChange={(e) => setDia(e.target.value)}
             className="rounded-full ring-1 ring-tinta-2/20 bg-panel px-4 py-2" />
      <a className="underline decoration-tinta-2/40 underline-offset-4 hover:decoration-marca"
         href={`/reporte/csv/?business=${negocio}`}>CSV</a>
      <a className="underline decoration-tinta-2/40 underline-offset-4 hover:decoration-marca"
         href={`/reporte/pdf/?business=${negocio}`}>PDF</a>
    </div>
  );

  return (
    <Marco titulo={resumen.business} subtitulo={esHoy ? "hoy" : resumen.date}
           acciones={acciones}>

      {/* El aviso ocupa una línea, no media pantalla: importa, pero no es la
          noticia del día. El detalle está a un clic para quien lo necesite. */}
      {extra?.camaras_caidas.length ? (
        <div className="col-span-12 flex flex-wrap items-baseline gap-x-3 gap-y-1
                        border-l-[3px] border-fila bg-fila/10 py-2 pl-3 pr-4 text-sm">
          <span className="font-semibold text-fila">
            {extra.camaras_caidas.length === 1
              ? "Una cámara sin señal"
              : `${extra.camaras_caidas.length} cámaras sin señal`}
          </span>
          <span className="text-tinta-2">
            Mientras tanto no se registran sus datos, así que faltan personas en la cuenta.
          </span>
          <button onClick={() => setVerCaidas(!verCaidas)}
                  className="underline underline-offset-4">
            {verCaidas ? "Ocultar" : "Ver cuáles"}
          </button>
          {verCaidas && (
            <ul className="mt-1 w-full text-tinta-2">
              {extra.camaras_caidas.map((c) => (
                <li key={c.camara}>
                  {c.camara} — sin datos desde {new Date(c.ultimo_latido).toLocaleString()}
                  {c.ultimo_error && `. ${c.ultimo_error}`}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}

      {/* Tarjetas KPI a todo ancho */}
      <div className="col-span-12">
        <TarjetasKpi kpis={kpis} />
      </div>

      {/* Fila: Mapa de calor + Recomendaciones IA */}
      <section className="col-span-12 lg:col-span-8 rounded-3xl bg-panel p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2 mb-4">
          <h2 className="font-display text-xl font-bold text-tinta">Mapa de calor de la tienda</h2>
          {camaras.length > 1 && (
            <select value={camara?.id ?? ""}
                    onChange={(e) => cambiarCamara(Number(e.target.value))}
                    className="rounded-full ring-1 ring-tinta-2/20 bg-panel px-4 py-2 text-sm">
              {camaras.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}{c.es_video ? " (video)" : ""}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="mt-3">
          {vista && camara ? (
            <Plano imagen={vista.image} video={vista.video} ancho={vista.width}
                   alto={vista.height} zonas={camara.zones} camaraId={camara.id} />
          ) : (
            <p className="rounded-3xl bg-panel p-10 text-center text-tinta-2">
              Todavía no hay ninguna cámara con video. Carga uno para empezar.
            </p>
          )}
        </div>
        {camara?.descripcion && (
          <p className="mt-2 text-tinta-2">{camara.descripcion}</p>
        )}
      </section>

      <div className="col-span-12 lg:col-span-4 h-full">
        <RecomendacionesIA recomendaciones={recomendacionesParaMostrar(extra?.recomendacion)} />
      </div>

      {/* Fila: Visitantes por hora + Últimos 7 días */}
      <section className="col-span-12 lg:col-span-8 rounded-3xl bg-panel p-6">
        <h2 className="font-display text-xl font-bold text-tinta">Visitantes por hora</h2>
        <p className="mb-2 text-sm text-tinta-2">Hoy frente al promedio de la semana</p>
        <GraficaHoras hoy={visitasPorHora} promedio={promedioHoras} />
      </section>
      <section className="col-span-12 lg:col-span-4 rounded-3xl bg-panel p-6">
        <h2 className="font-display text-xl font-bold text-tinta">Últimos 7 días</h2>
        <p className="mb-2 text-sm text-tinta-2">Visitantes por día</p>
        <BarrasSemana semana={semana} />
      </section>

      {/* Resumen en palabras y Cinta del día */}
      <div className="col-span-12">
        <ResumenEnPalabras visitantes={resumen.total_visitors}
                           horaPico={resumen.peak_hour}
                           esperaSegundos={resumen.avg_queue_seconds} />
      </div>

      <div className="col-span-12">
        <CintaDelDia horas={resumen.hourly}
                     horasConAviso={eventos.map((e) => new Date(e.occurred_at).getHours())}
                     ahora={esHoy ? new Date().getHours() : undefined} />
      </div>

      {/* Zonas: comparar es el trabajo, así que barras y no una tabla de cifras. */}
      <section className="col-span-12 md:col-span-7">
        <h2 className="font-display text-xl font-bold text-tinta">Por zona</h2>
        {resumen.zones.length ? (
          <ul className="mt-4 space-y-3">
            {resumen.zones.map((z) => (
              <li key={z.zone_name}
                  className="grid grid-cols-[7rem_1fr_auto] items-center gap-3">
                <span className="truncate">
                  {z.zone_name}
                  <span className="ml-1 text-sm text-tinta-2">
                    {TIPO_ZONA[z.zone_kind] ?? z.zone_kind}
                  </span>
                </span>
                <span className="h-2.5 rounded-full bg-tinta-2/15">
                  <span className={`block h-full rounded-full ${
                    z.zone_kind === "queue" ? "bg-fila"
                    : z.zone_kind === "counter" || z.zone_kind === "staff" ? "bg-personal"
                    : "bg-calma"}`}
                      style={{ width: `${Math.max((z.visitors / topeZona) * 100, 2)}%` }} />
                </span>
                <span className="tabular-nums text-sm">
                  {z.visitors} {z.visitors === 1 ? "persona" : "personas"}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 max-w-[50ch] text-tinta-2">
            Todavía no hay zonas medidas.{rubro.zonas.length
              ? ` Para un negocio como el tuyo conviene dibujar: ${
                  rubro.zonas.map((z) => z.name).join(", ")}.`
              : " Dibuja una sobre la cámara y analiza el video."}
          </p>
        )}
      </section>

      {/* Lo que pasó: frases, no una tabla con claves del sistema. */}
      <section className="col-span-12 md:col-span-5">
        <h2 className="font-display text-xl font-bold text-tinta">Lo que pasó</h2>
        {eventos.length ? (
          <ul className="mt-4 space-y-2">
            {[...eventos]
              .sort((x, y) => y.occurred_at.localeCompare(x.occurred_at))
              .slice(0, 6)
              .map((e) => (
              <li key={e.id} className="flex gap-3">
                <time className="w-12 shrink-0 tabular-nums text-tinta-2">
                  {new Date(e.occurred_at).toLocaleTimeString([], {
                    hour: "2-digit", minute: "2-digit" })}
                </time>
                <span>
                  {(QUE_PASO[e.kind]
                    ?? ((v: number, z: string) => `${e.kind} en ${z} (${v})`))(e.value, e.zone)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-tinta-2">Un día tranquilo: nada que reportar.</p>
        )}
      </section>

      <section className="col-span-12">
        <h2 className="font-display text-xl font-bold text-tinta">
          Comparado con negocios como el tuyo
        </h2>
        {extra?.comparativa ? (
          <>
            <p className="mt-2 text-sm text-tinta-2">
              Frente a {extra.comparativa.negocios_comparados} negocios anónimos del mismo
              tipo, en los últimos {extra.comparativa.ventana_dias} días.
            </p>
            <div className="overflow-x-auto">
              <table className="mt-3 w-full text-left">
                <thead className="text-sm text-tinta-2">
                  <tr>
                    <th className="py-2 font-medium">Métrica</th>
                    <th className="font-medium">Tú</th>
                    <th className="font-medium">La mitad de ellos</th>
                    <th className="font-medium">Tu puesto</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(extra.comparativa)
                    .filter(([, v]) => v && typeof v === "object" && v.propio != null)
                    .map(([clave, v]: [string, any]) => (
                      <tr key={clave} className="border-t border-tinta-2/15">
                        <td className="py-2">{METRICAS_COMPARATIVA[clave] ?? clave}</td>
                        <td className="tabular-nums font-semibold">{v.propio}</td>
                        <td className="tabular-nums text-tinta-2">{v.mediana_pares}</td>
                        <td className="tabular-nums">mejor que el {v.percentil}%</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="mt-2 max-w-[60ch] text-tinta-2">
            Faltan negocios de tu tipo para poder comparar sin que nadie sea
            identificable. Hacen falta al menos cinco.
          </p>
        )}
      </section>
    </Marco>
  );
}