// La frontera entre lo que guarda el sistema y lo que lee el dueño, igual que
// TIPO_ZONA y QUE_PASO en Panel.tsx. Aquí `long_queue` deja de existir.
export type Tipo =
  | "long_queue"
  | "crowded_queue"
  | "empty_counter"
  | "overcrowding"
  | "entry_peak"
  | "low_traffic";

export const AVISOS: Record<Tipo, {
  titulo: string;
  unidad: "minutos" | "personas";
  cuando: (n: number) => string;
}> = {
  long_queue: {
    titulo: "La fila se hace larga",
    unidad: "minutos",
    cuando: (n) => `si alguien espera más de ${n} min en la fila`,
  },
  crowded_queue: {
    titulo: "Se junta gente en la fila",
    unidad: "personas",
    cuando: (n) => `si hay más de ${n} personas en la fila`,
  },
  empty_counter: {
    titulo: "La caja se queda sola",
    unidad: "personas",
    cuando: () => "si la caja se queda sin nadie atendiendo",
  },
  overcrowding: {
    titulo: "El local se llena",
    unidad: "personas",
    cuando: (n) => `si hay más de ${n} personas a la vez`,
  },
  entry_peak: {
    titulo: "Pico de entradas",
    unidad: "personas",
    cuando: (n) => `si entran más de ${n} personas por hora`,
  },
  low_traffic: {
    titulo: "Poco tráfico en una zona",
    unidad: "personas",
    cuando: (n) => `si hay menos de ${n} personas en una zona`,
  },
};

// El sistema mide segundos; el dueño piensa en minutos. La conversión vive
// aquí y no en el formulario, para que el test la cubra.
export const aUmbral = (tipo: Tipo, valor: number) =>
  AVISOS[tipo].unidad === "minutos" ? Math.round(valor * 60) : valor;

export const deUmbral = (tipo: Tipo, umbral: number) =>
  AVISOS[tipo].unidad === "minutos" ? Math.round(umbral / 60) : umbral;

export type Accion = "avisar" | "abrir_caja" | "mensaje_personal" | "registrar";

export const ACCIONES: Record<Accion, { titulo: string }> = {
  avisar: { titulo: "Avisarme" },
  abrir_caja: { titulo: "Pedir que abran la segunda caja" },
  mensaje_personal: { titulo: "Mandar mensaje al personal" },
  registrar: { titulo: "Registrar en el reporte" },
};

export const COLOR_TIPO: Record<Tipo, "fila" | "lleno" | "calma" | "personal"> = {
  long_queue: "fila",
  crowded_queue: "fila",
  overcrowding: "lleno",
  entry_peak: "lleno",
  empty_counter: "calma",
  low_traffic: "calma",
};

export function tonoDeEntrega(e: { tipo: Tipo; accion: Accion }): "fila" | "lleno" | "calma" | "personal" {
  if (e.accion !== "avisar") return "personal";
  return COLOR_TIPO[e.tipo];
}

export interface Plantilla {
  id: string;
  titulo: string;
  descripcion: string;
  tipo_evento: Tipo;
  umbral: number;
  accion: Accion;
  texto: string;
  canal: string;
  destino: string;
}

export const PLANTILLAS: Plantilla[] = [
  {
    id: "abrir_segunda_caja",
    titulo: "Abre la segunda caja si la fila pasa de 4 min",
    descripcion: "Pide a un empleado que abra otra caja cuando la espera sube",
    tipo_evento: "long_queue",
    umbral: 240,
    accion: "abrir_caja",
    texto: "",
    canal: "webhook",
    destino: "",
  },
  {
    id: "caja_sola",
    titulo: "Avísame si la caja queda sola",
    descripcion: "Te avisa cuando no hay nadie atendiendo en la caja",
    tipo_evento: "empty_counter",
    umbral: 1,
    accion: "avisar",
    texto: "",
    canal: "email",
    destino: "dueno@mitienda.co",
  },
  {
    id: "personal_lleno",
    titulo: "Avisa al personal si el local pasa de 25 personas",
    descripcion: "Manda un mensaje al equipo cuando hay mucha gente",
    tipo_evento: "overcrowding",
    umbral: 25,
    accion: "mensaje_personal",
    texto: "El local está muy lleno, por favor revisen",
    canal: "webhook",
    destino: "",
  },
  {
    id: "registrar_picos",
    titulo: "Registra los picos de entradas en el reporte",
    descripcion: "Guarda en el reporte cuando entra mucha gente de golpe",
    tipo_evento: "entry_peak",
    umbral: 30,
    accion: "registrar",
    texto: "",
    canal: "webhook",
    destino: "",
  },
];

export type Regla = {
  tipo_evento: Tipo;
  umbral: number | null;
  canal: string;
  destino: string;
};

export function frase(regla: Regla): string {
  const donde = regla.canal === "email"
    ? `por correo a ${regla.destino}`
    : "al webhook configurado";
  const cuando = AVISOS[regla.tipo_evento].cuando(
    deUmbral(regla.tipo_evento, regla.umbral ?? 0));
  return `Te avisamos ${cuando}, ${donde}.`;
}

export function fraseRegla(r: Regla & { accion: Accion; texto?: string }): string {
  const cuando = AVISOS[r.tipo_evento].cuando(
    deUmbral(r.tipo_evento, r.umbral ?? 0));
  let accionTexto = "";
  switch (r.accion) {
    case "avisar":
      accionTexto = `avísame${r.canal === "email" ? " por correo" : ""}`;
      break;
    case "abrir_caja":
      accionTexto = "pedir a un empleado que abra la segunda caja";
      break;
    case "mensaje_personal":
      accionTexto = "mandar mensaje al personal";
      break;
    case "registrar":
      accionTexto = "registrar en el reporte";
      break;
  }
  return `${cuando[0].toUpperCase()}${cuando.slice(1)} → ${accionTexto}.`;
}