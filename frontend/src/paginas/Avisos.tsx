import { useEffect, useState } from "react";
import { Marco } from "../componentes/Marco";
import { AVISOS, aUmbral, deUmbral, frase, type Regla, type Tipo } from "../avisos";
import { borrar, get, pedirPut, post } from "../api";

type Entrega = { tipo: string; mensaje: string; resultado: string; cuando: string };
type Datos = {
  reglas: (Regla & { id: number; minutos_silencio: number; activa: boolean })[];
  sugeridos: Partial<Record<Tipo, number>>;
  horario: { abre: string; cierra: string };
  recientes: Entrega[];
};

const RESULTADO: Record<string, string> = {
  enviada: "te avisamos",
  silenciada: "no se repitió tan seguido",
  fuera_hora: "estaba cerrado, no te despertamos",
  fallo: "no se pudo entregar",
};

export default function Avisos({ negocio }: { negocio: number }) {
  const [datos, setDatos] = useState<Datos | null>(null);
  const [tipo, setTipo] = useState<Tipo>("long_queue");
  const [cuanto, setCuanto] = useState(5);
  const [destino, setDestino] = useState("");
  const [error, setError] = useState("");

  const cargar = () =>
    get<Datos>(`/api/avisos/?business=${negocio}`).then(setDatos).catch((e) => setError(e.message));

  useEffect(() => { cargar(); }, [negocio]);

  // Al cambiar de tipo, el formulario propone lo que sugiere el rubro: el dueño
  // corrige un número razonable en vez de inventarse uno desde cero.
  useEffect(() => {
    const sugerido = datos?.sugeridos[tipo];
    if (sugerido !== undefined) setCuanto(deUmbral(tipo, sugerido));
  }, [tipo, datos]);

  const crear = async () => {
    setError("");
    try {
      await post(`/api/avisos/?business=${negocio}`, {
        tipo_evento: tipo, canal: destino.includes("@") ? "email" : "webhook",
        destino, umbral: aUmbral(tipo, cuanto), minutos_silencio: 15,
      });
      setDestino("");
      cargar();
    } catch (e) { setError((e as Error).message); }
  };

  if (error && !datos) return <Marco titulo="Avisos"><p className="col-span-12">{error}</p></Marco>;
  if (!datos) return <Marco titulo="Avisos"><p className="col-span-12">Cargando…</p></Marco>;

  return (
    <Marco titulo="Avisos" subtitulo="qué te avisamos y cuándo">
      <section className="col-span-12 lg:col-span-7">
        <h2 className="mb-3 font-display text-xl font-bold">Lo que te avisamos hoy</h2>
        {datos.reglas.length === 0 && (
          <p className="text-tinta-2">
            Todavía no te avisamos de nada. Elige abajo qué quieres saber y a dónde.
          </p>
        )}
        <ul className="flex flex-col gap-3">
          {datos.reglas.map((r) => (
            <li key={r.id} className="rounded-lg border border-tinta-2/15 p-4">
              <p className="font-medium">{AVISOS[r.tipo_evento].titulo}</p>
              <p className="text-tinta-2">{frase(r)}</p>
              <div className="mt-2 flex gap-4">
                <button className="underline" onClick={async () => {
                  await pedirPut(`/api/avisos/${r.id}/?business=${negocio}`,
                                 { activa: !r.activa });
                  cargar();
                }}>{r.activa ? "Silenciar" : "Volver a avisar"}</button>
                <button className="underline" onClick={async () => {
                  await borrar(`/api/avisos/${r.id}/?business=${negocio}`);
                  cargar();
                }}>Quitar</button>
              </div>
            </li>
          ))}
        </ul>

        <h2 className="mb-3 mt-8 font-display text-xl font-bold">Avisarme también</h2>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col">Qué
            <select value={tipo} onChange={(e) => setTipo(e.target.value as Tipo)}>
              {(Object.keys(AVISOS) as Tipo[]).map((t) => (
                <option key={t} value={t}>{AVISOS[t].titulo}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col">A partir de ({AVISOS[tipo].unidad})
            <input type="number" min={1} value={cuanto}
                   onChange={(e) => setCuanto(Number(e.target.value))} />
          </label>
          <label className="flex flex-col">A dónde (correo o webhook https://)
            <input value={destino} onChange={(e) => setDestino(e.target.value)}
                   placeholder="tucorreo@tutienda.co" />
          </label>
          <button className="underline" onClick={crear} disabled={!destino}>Guardar</button>
        </div>
        {error && <p className="mt-2 text-fila">{error}</p>}
      </section>

      <section className="col-span-12 lg:col-span-5">
        <h2 className="mb-3 font-display text-xl font-bold">Horario del local</h2>
        <p className="mb-2 text-tinta-2">
          Fuera de este horario no te mandamos nada. Las cámaras siguen midiendo:
          lo que se apaga es el aviso, no la cuenta. Dejar las dos horas iguales
          es avisar a cualquier hora.
        </p>
        <div className="flex items-end gap-3">
          <label className="flex flex-col">Abre
            <input type="time" defaultValue={datos.horario.abre} id="abre" />
          </label>
          <label className="flex flex-col">Cierra
            <input type="time" defaultValue={datos.horario.cierra} id="cierra" />
          </label>
          <button className="underline" onClick={async () => {
            const hora = (id: string) =>
              (document.getElementById(id) as HTMLInputElement).value;
            await pedirPut(`/api/avisos/horario/?business=${negocio}`,
                           { abre: hora("abre"), cierra: hora("cierra") });
            cargar();
          }}>Guardar horario</button>
        </div>

        <h2 className="mb-3 mt-8 font-display text-xl font-bold">Últimos avisos</h2>
        {datos.recientes.length === 0
          ? <p className="text-tinta-2">Todavía no ha pasado nada que avisar.</p>
          : (
            <ul className="flex flex-col gap-2">
              {datos.recientes.map((e, i) => (
                <li key={i} className="text-tinta-2">
                  <span className="text-tinta">{new Date(e.cuando).toLocaleString()}</span>
                  {" — "}{e.mensaje} ({RESULTADO[e.resultado] ?? e.resultado})
                </li>
              ))}
            </ul>
          )}
      </section>
    </Marco>
  );
}
