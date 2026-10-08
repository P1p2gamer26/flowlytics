type Hora = { hour: number; occupancy_avg: number; visitors: number };

/** Umbrales de "como estuvo la tienda a esa hora", relativos al dia.
 *
 * Relativos y no absolutos a proposito: doce personas es un dia flojo en un
 * supermercado y una avalancha en una droguería de barrio. Lo que el dueño
 * reconoce es su propio pico, no un numero universal. */
function tono(ocupacion: number, pico: number, hubo_aviso: boolean) {
  if (pico <= 0 || ocupacion <= 0) return "vacia";
  // El rojo significa "aqui hubo un problema" (fila larga, aforo excedido), no
  // "esta fue la hora mas alta": el maximo de cualquier dia es siempre el
  // maximo, asi que pintarlo de rojo convertiria el color en decoracion.
  if (hubo_aviso) return "fila";
  return ocupacion / pico >= 0.45 ? "lleno" : "calma";
}

const COLOR = {
  vacia: "bg-noche-2",
  calma: "bg-calma",
  lleno: "bg-lleno",
  fila: "bg-fila",
} as const;

const PALABRA = {
  vacia: "sin gente",
  calma: "tranquila",
  lleno: "con movimiento",
  fila: "hubo un aviso",
} as const;

/**
 * El dia entero como una tira de 24 horas.
 *
 * Sustituye al grafico de barras anterior, que solo dibujaba las horas CON
 * datos: un dia con una sola hora activa se veia como un bloque solido de
 * color y no se distinguia de un dia lleno. Aqui las 24 horas estan siempre,
 * asi que una hora punta se lee como lo que es — un pico — y una tienda vacia
 * se ve vacia.
 */
export function CintaDelDia({ horas, horasConAviso = [], ahora }: {
  horas: Hora[]; horasConAviso?: number[]; ahora?: number;
}) {
  const porHora = new Map(horas.map((h) => [h.hour, h]));
  const avisos = new Set(horasConAviso);
  const pico = Math.max(...horas.map((h) => h.occupancy_avg), 0);
  const todas = Array.from({ length: 24 }, (_, h) => porHora.get(h));

  return (
    <div className="rounded-3xl bg-panel p-6">
      <div className="flex h-40 items-end gap-[3px]">
        {todas.map((h, i) => {
          const ocupacion = h?.occupancy_avg ?? 0;
          const t = tono(ocupacion, pico, avisos.has(i));
          const alto = pico > 0 ? Math.max((ocupacion / pico) * 100, 3) : 3;
          const esAhora = ahora === i;
          return (
            <div
              key={i}
              className={`hora flex-1 rounded-[2px] ${COLOR[t]} ${
                esAhora ? "ring-2 ring-papel/70" : ""
              }`}
              style={{ height: `${alto}%`, ["--i" as string]: i }}
              title={`${i}:00 — ${PALABRA[t]}${
                h ? `, ${h.visitors} personas` : ""
              }`}
            />
          );
        })}
      </div>

      <div className="mt-3 flex justify-between font-sans text-xs text-tinta-clara">
        <span>medianoche</span>
        <span>mediodía</span>
        <span>medianoche</span>
      </div>
    </div>
  );
}

/** La frase que el dueño lee primero. En su idioma, no en el del sistema. */
export function ResumenEnPalabras({ visitantes, horaPico, esperaSegundos }: {
  visitantes: number;
  horaPico: number | null;
  esperaSegundos: number | null;
}) {
  if (!visitantes) {
    return (
      <p className="max-w-[60ch] font-display text-titular font-bold text-tinta leading-snug">
        Hoy todavía no se ha registrado nadie. Cuando una cámara esté analizando,
        el día aparece aquí.
      </p>
    );
  }

  const hora = horaPico === null ? null : `${horaPico}:00`;
  const espera = esperaSegundos && esperaSegundos >= 60
    ? `${Math.round(esperaSegundos / 60)} minutos`
    : null;

  return (
    <p className="max-w-[60ch] font-display text-titular font-bold text-tinta leading-snug">
      Entraron <strong className="font-display font-extrabold text-acento">{visitantes}</strong> personas.
      {hora && <> El momento más movido fue a las <strong className="font-display font-extrabold text-acento">{hora}</strong>.</>}
      {espera && <> La fila llegó a durar <strong className="font-display font-extrabold text-acento">{espera}</strong>.</>}
    </p>
  );
}
