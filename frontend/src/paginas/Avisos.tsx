import { useEffect, useState } from "react";
import { Marco } from "../componentes/Marco";
import {
  ACCIONES, AVISOS, PLANTILLAS, aUmbral, deUmbral, fraseRegla, tonoDeEntrega,
  type Accion, type Plantilla, type Regla, type Tipo,
} from "../avisos";
import { borrar, get, pedirPut, post } from "../api";

type ReglaApi = Regla & { id: number; minutos_silencio: number; activa: boolean;
                          accion: Accion; texto: string };
type Entrega = { id: number; tipo: Tipo; mensaje: string; resultado: string; camara: string;
                 accion: Accion; simulado: boolean; cuando: string };
type Datos = {
  reglas: ReglaApi[];
  sugeridos: Partial<Record<Tipo, number>>;
  horario: { abre: string; cierra: string };
  recientes: Entrega[];
};
type Tono = "fila" | "lleno" | "calma" | "personal";

const RESULTADO: Record<string, string> = {
  enviada: "te avisamos",
  registrada: "registrado",
  silenciada: "no se repitió tan seguido",
  fuera_hora: "estaba cerrado",
  fallo: "no se pudo entregar",
};

// Clases completas y literales: Tailwind no detecta las que se arman con plantillas.
const TONO: Record<Tono, { borde: string; fondo: string; punto: string; texto: string }> = {
  fila: { borde: "border-l-fila", fondo: "bg-fila/10", punto: "bg-fila", texto: "text-fila" },
  lleno: { borde: "border-l-lleno", fondo: "bg-lleno/15", punto: "bg-lleno", texto: "text-lleno" },
  calma: { borde: "border-l-calma", fondo: "bg-calma/10", punto: "bg-calma", texto: "text-calma" },
  personal: { borde: "border-l-personal", fondo: "bg-personal/10", punto: "bg-personal", texto: "text-personal" },
};

const TONO_TIPO: Record<Tipo, Tono> = {
  long_queue: "fila", crowded_queue: "fila", overcrowding: "lleno",
  entry_peak: "lleno", empty_counter: "calma", low_traffic: "calma",
};

function Icono({ tono }: { tono: Tono }) {
  return (
    <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${TONO[tono].fondo} ${TONO[tono].texto}`}>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.7 21a2 2 0 0 1-3.4 0" />
      </svg>
    </span>
  );
}

function Vacio({ titulo, texto }: { titulo: string; texto: string }) {
  return (
    <div className="flex flex-col items-center rounded-3xl
                    bg-panel px-6 py-8 text-center">
      <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"
           className="mb-3 text-tinta-clara" aria-hidden="true">
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.7 21a2 2 0 0 1-3.4 0" />
      </svg>
      <p className="font-display text-lg font-bold">{titulo}</p>
      <p className="text-tinta-2">{texto}</p>
    </div>
  );
}

const hora = (iso: string) =>
  new Date(iso).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" });

export default function Avisos({ negocio }: { negocio: number }) {
  const [datos, setDatos] = useState<Datos | null>(null);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const [nuevas, setNuevas] = useState<number[]>([]);
  const [simular, setSimular] = useState<Tipo>("long_queue");
  // formulario propio
  const [tipo, setTipo] = useState<Tipo>("long_queue");
  const [cuanto, setCuanto] = useState(5);
  const [accion, setAccion] = useState<Accion>("avisar");
  const [destino, setDestino] = useState("");
  const [texto, setTexto] = useState("");

  const cargar = () =>
    get<Datos>(`/api/avisos/?business=${negocio}`).then(setDatos).catch((e) => setError(e.message));

  useEffect(() => { cargar(); }, [negocio]);

  // Al cambiar de tipo se propone lo que sugiere el rubro.
  useEffect(() => {
    const sugerido = datos?.sugeridos[tipo];
    if (sugerido !== undefined) setCuanto(deUmbral(tipo, sugerido));
  }, [tipo, datos]);

  const intentar = async (accionAsync: () => Promise<unknown>) => {
    setError("");
    try { await accionAsync(); await cargar(); } catch (e) { setError((e as Error).message); }
  };

  const lanzarSimulacion = () => intentar(async () => {
    const r = await post<{ entregas: Entrega[]; sin_reglas: boolean }>(
      `/api/avisos/simular/?business=${negocio}`, { tipo_evento: simular });
    setNuevas(r.entregas.map((e) => e.id));
    setAviso(r.sin_reglas ? "Aún no tienes reglas: activa una plantilla abajo." : "");
  });

  const activar = (p: Plantilla) => intentar(() =>
    post(`/api/avisos/?business=${negocio}`, {
      tipo_evento: p.tipo_evento, canal: p.canal, destino: p.destino, umbral: p.umbral,
      minutos_silencio: 15, accion: p.accion, texto: p.texto,
    }));

  const crear = () => intentar(async () => {
    await post(`/api/avisos/?business=${negocio}`, {
      tipo_evento: tipo, accion, texto: accion === "avisar" ? "" : texto,
      canal: destino.includes("@") ? "email" : "webhook",
      destino: accion === "avisar" ? destino : "",
      umbral: aUmbral(tipo, cuanto), minutos_silencio: 15,
    });
    setDestino(""); setTexto("");
  });

  if (error && !datos) return <Marco titulo="Avisos"><p className="col-span-12">{error}</p></Marco>;
  if (!datos) return <Marco titulo="Avisos"><p className="col-span-12">Cargando…</p></Marco>;

  const yaActiva = (p: Plantilla) =>
    datos.reglas.some((r) => r.tipo_evento === p.tipo_evento && r.accion === p.accion);

  return (
    <Marco titulo="Avisos" subtitulo="qué hacemos cuando pasa algo en tu local"
           acciones={
             <div className="flex items-center gap-2">
               <label className="sr-only" htmlFor="sim-tipo">Qué simular</label>
               <select id="sim-tipo" value={simular} className="rounded-full bg-panel px-4 py-2 ring-1 ring-tinta-2/20"
                       onChange={(e) => setSimular(e.target.value as Tipo)}>
                 {(Object.keys(AVISOS) as Tipo[]).map((t) => (
                   <option key={t} value={t}>{AVISOS[t].titulo}</option>
                 ))}
               </select>
               <button onClick={lanzarSimulacion}
                       className="rounded-full bg-acento px-5 py-2 font-semibold text-white hover:opacity-90">
                 Simular evento
               </button>
             </div>
           }>
      {(aviso || error) && (
        <p className={`col-span-12 ${error ? "text-fila" : "text-tinta-2"}`} role="status">
          {error || aviso}
        </p>
      )}

      <section className="col-span-12 flex flex-col gap-8 lg:col-span-7">
        <div>
          <h2 className="mb-3 font-display text-xl font-bold">Tus automatizaciones</h2>
          {datos.reglas.length === 0 ? (
            <Vacio titulo="Todavía no tienes automatizaciones"
                   texto="Activa una plantilla para empezar." />
          ) : (
            <ul className="flex flex-col gap-3">
              {datos.reglas.map((r) => (
                <li key={r.id}
                    className={`flex items-center gap-4 rounded-3xl bg-panel p-5
                                ${r.activa ? "" : "opacity-60"}`}>
                  <Icono tono={TONO_TIPO[r.tipo_evento]} />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{AVISOS[r.tipo_evento].titulo}</p>
                    <p className="text-tinta-2">{fraseRegla(r)}</p>
                    {r.texto && <p className="text-sm text-tinta-2">“{r.texto}”</p>}
                  </div>
                  <button role="switch" aria-checked={r.activa}
                          aria-label={`${r.activa ? "Pausar" : "Activar"}: ${AVISOS[r.tipo_evento].titulo}`}
                          onClick={() => intentar(() =>
                            pedirPut(`/api/avisos/${r.id}/?business=${negocio}`, { activa: !r.activa }))}
                          className={`relative h-6 w-11 shrink-0 rounded-full transition-colors
                                      ${r.activa ? "bg-calma" : "bg-tinta-clara"}`}>
                    <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all
                                      ${r.activa ? "left-[22px]" : "left-0.5"}`} />
                  </button>
                  <button className="text-tinta-2 underline hover:text-fila"
                          onClick={() => intentar(() =>
                            borrar(`/api/avisos/${r.id}/?business=${negocio}`))}>Quitar</button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <h2 className="mb-3 font-display text-xl font-bold">Plantillas listas</h2>
          <ul className="grid gap-3 sm:grid-cols-2">
            {PLANTILLAS.map((p) => (
              <li key={p.id} className="flex flex-col justify-between gap-3 rounded-3xl
                                        bg-panel p-5">
                <div>
                  <p className="font-medium">{p.titulo}</p>
                  <p className="text-sm text-tinta-2">{p.descripcion}</p>
                </div>
                <button disabled={yaActiva(p)} onClick={() => activar(p)}
                        className="self-start rounded-full bg-marca px-4 py-1.5 font-semibold
                                   text-white hover:bg-marca-2 disabled:bg-papel
                                   disabled:text-tinta-2 disabled:hover:bg-papel">
                  {yaActiva(p) ? "Ya activa" : "Activar"}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h2 className="mb-3 font-display text-xl font-bold">Crea la tuya</h2>
          <div className="flex flex-wrap items-end gap-3 rounded-3xl bg-panel p-5">
            <label className="flex flex-col text-sm">Cuando
              <select value={tipo} onChange={(e) => setTipo(e.target.value as Tipo)}
                      className="rounded-full bg-panel px-4 py-2 ring-1 ring-tinta-2/20 text-base">
                {(Object.keys(AVISOS) as Tipo[]).map((t) => (
                  <option key={t} value={t}>{AVISOS[t].titulo}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-sm">Pase de ({AVISOS[tipo].unidad})
              <input type="number" min={1} value={cuanto} onChange={(e) => setCuanto(Number(e.target.value))}
                     className="w-24 rounded-full bg-panel px-4 py-2 ring-1 ring-tinta-2/20 text-base" />
            </label>
            <label className="flex flex-col text-sm">→ Entonces
              <select value={accion} onChange={(e) => setAccion(e.target.value as Accion)}
                      className="rounded-full bg-panel px-4 py-2 ring-1 ring-tinta-2/20 text-base">
                {(Object.keys(ACCIONES) as Accion[]).map((a) => (
                  <option key={a} value={a}>{ACCIONES[a].titulo}</option>
                ))}
              </select>
            </label>
            {accion === "avisar" ? (
              <label className="flex flex-col text-sm">A dónde (correo o https://)
                <input value={destino} onChange={(e) => setDestino(e.target.value)}
                       placeholder="tucorreo@tutienda.co"
                       className="rounded-full bg-panel px-4 py-2 ring-1 ring-tinta-2/20 text-base" />
              </label>
            ) : (
              <label className="flex flex-col text-sm">Mensaje (opcional)
                <input value={texto} onChange={(e) => setTexto(e.target.value)}
                       placeholder="Ej: Refuercen la caja"
                       className="rounded-full bg-panel px-4 py-2 ring-1 ring-tinta-2/20 text-base" />
              </label>
            )}
            <button onClick={crear} disabled={accion === "avisar" && !destino}
                    className="rounded-full bg-marca px-5 py-2 font-semibold text-white hover:bg-marca-2 disabled:opacity-40">
              Crear automatización
            </button>
          </div>
        </div>
      </section>

      <section className="col-span-12 flex flex-col gap-8 lg:col-span-5">
        <div>
          <h2 className="mb-3 font-display text-xl font-bold">Últimos avisos</h2>
          {datos.recientes.length === 0 ? (
            <Vacio titulo="Todo tranquilo por ahora"
                   texto="Cuando pase algo en tu local, lo verás aquí al instante." />
          ) : (
            <ul className="flex flex-col gap-2">
              {datos.recientes.map((e) => {
                const t = TONO[tonoDeEntrega({ tipo: e.tipo, accion: e.accion })];
                return (
                  <li key={e.id}
                      className={`rounded-2xl border-l-4 ${t.borde} ${t.fondo} px-4 py-3
                                  ${nuevas.includes(e.id) ? "aviso-nuevo" : ""}`}>
                    <div className="flex flex-wrap items-center gap-x-2 text-sm text-tinta-2">
                      <span className={`inline-block h-2 w-2 rounded-full ${t.punto}`} aria-hidden="true" />
                      <span className="font-medium text-tinta">{hora(e.cuando)}</span>
                      <span>{e.camara || "—"}</span>
                      <span>· {AVISOS[e.tipo]?.titulo ?? e.tipo}</span>
                      {e.simulado && (
                        <span className="rounded bg-tinta/10 px-1.5 text-xs">simulado</span>
                      )}
                    </div>
                    <p>{e.mensaje}</p>
                    <p className="text-sm text-tinta-2">{RESULTADO[e.resultado] ?? e.resultado}</p>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div>
          <h2 className="mb-3 font-display text-xl font-bold">Horario del local</h2>
          <p className="mb-2 text-sm text-tinta-2">
            Fuera de este horario no te mandamos nada. Si las dos horas son iguales,
            avisamos a cualquier hora.
          </p>
          <div className="flex items-end gap-3">
            <label className="flex flex-col text-sm">Abre
              <input type="time" defaultValue={datos.horario.abre} id="abre"
                     className="rounded-full bg-panel px-4 py-2 ring-1 ring-tinta-2/20 text-base" />
            </label>
            <label className="flex flex-col text-sm">Cierra
              <input type="time" defaultValue={datos.horario.cierra} id="cierra"
                     className="rounded-full bg-panel px-4 py-2 ring-1 ring-tinta-2/20 text-base" />
            </label>
            <button className="underline" onClick={() => {
              const v = (id: string) => (document.getElementById(id) as HTMLInputElement).value;
              intentar(() => pedirPut(`/api/avisos/horario/?business=${negocio}`,
                                      { abre: v("abre"), cierra: v("cierra") }));
            }}>Guardar horario</button>
          </div>
        </div>
      </section>
    </Marco>
  );
}
