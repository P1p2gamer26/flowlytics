// La frontera entre lo que guarda el sistema y lo que lee el dueño, igual que
// TIPO_ZONA y QUE_PASO en Panel.tsx. Aquí `long_queue` deja de existir.
export type Tipo = "long_queue" | "crowded_queue" | "empty_counter" | "overcrowding";

export const AVISOS: Record<Tipo, {
  titulo: string;
  unidad: "minutos" | "personas";
  cuando: (n: number) => string;
}> = {
  long_queue: {
    titulo: "La fila se hace larga", unidad: "minutos",
    cuando: (n) => `si alguien espera más de ${n} min en la fila`,
  },
  crowded_queue: {
    titulo: "Se junta gente en la fila", unidad: "personas",
    cuando: (n) => `si hay más de ${n} personas en la fila`,
  },
  empty_counter: {
    titulo: "La caja se queda sola", unidad: "personas",
    cuando: () => "si la caja se queda sin nadie atendiendo",
  },
  overcrowding: {
    titulo: "El local se llena", unidad: "personas",
    cuando: (n) => `si hay más de ${n} personas a la vez`,
  },
};

// El sistema mide segundos; el dueño piensa en minutos. La conversión vive
// aquí y no en el formulario, para que el test la cubra.
export const aUmbral = (tipo: Tipo, valor: number) =>
  AVISOS[tipo].unidad === "minutos" ? Math.round(valor * 60) : valor;

export const deUmbral = (tipo: Tipo, umbral: number) =>
  AVISOS[tipo].unidad === "minutos" ? Math.round(umbral / 60) : umbral;

export type Regla = {
  tipo_evento: Tipo; umbral: number | null; canal: string; destino: string;
};

export function frase(regla: Regla): string {
  const donde = regla.canal === "email"
    ? `por correo a ${regla.destino}`
    : "al webhook configurado";
  const cuando = AVISOS[regla.tipo_evento].cuando(
    deUmbral(regla.tipo_evento, regla.umbral ?? 0));
  return `Te avisamos ${cuando}, ${donde}.`;
}
