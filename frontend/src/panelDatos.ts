export type Recomendacion = {
  id: string;
  zona: string;
  texto: string;
  dato: string;
  impacto: string;
  prioridad: "alta" | "media" | "baja";
};

export const RECOMENDACIONES_DEMO: Recomendacion[] = [
  {
    id: "demo-1",
    zona: "Pasillo 3",
    texto: "Mover snacks junto a caja: 8% del tráfico pasa por ahí sin comprar",
    dato: "8% del tráfico total pasa por pasillo 3 sin conversión",
    impacto: "+6% en ventas de impulso",
    prioridad: "alta",
  },
  {
    id: "demo-2",
    zona: "Cajas",
    texto: "Abrir segunda caja 15:00-16:00: fila supera 4 min de espera",
    dato: "Espera media 4:12 min entre 15:00-16:00",
    impacto: "-35% abandono en hora pico",
    prioridad: "alta",
  },
  {
    id: "demo-3",
    zona: "Caja 1",
    texto: "Caja 1 sola 12 min a las 13:10: reforzar turno de comida",
    dato: "Cobertura personal cayó al 67% a las 13:10",
    impacto: "+8 tickets/hora en franja comida",
    prioridad: "media",
  },
  {
    id: "demo-4",
    zona: "Horario",
    texto: "Extender apertura 30 min: 12% de visitantes llegan antes de abrir",
    dato: "12% del tráfico diario en los 30 min previos a apertura",
    impacto: "+4% facturación diaria",
    prioridad: "baja",
  },
];

export function recomendacionesParaMostrar(real: string | undefined): Recomendacion[] {
  if (real && real.trim()) {
    return [
      {
        id: "real",
        zona: "General",
        texto: real.trim(),
        dato: "Basado en los datos de hoy",
        impacto: "",
        prioridad: "media",
      },
      ...RECOMENDACIONES_DEMO.slice(0, 3),
    ];
  }
  return RECOMENDACIONES_DEMO;
}

export function variacion(actual: number, previo: number): number | null {
  if (previo <= 0) return null;
  return Math.round(((actual - previo) / previo) * 100);
}

export function promedioPorHora(semanaPrevia: number[][]): number[] {
  const suma = new Array(24).fill(0);
  let dias = 0;
  for (const dia of semanaPrevia) {
    if (dia.length === 24) {
      for (let h = 0; h < 24; h++) {
        suma[h] += dia[h];
      }
      dias++;
    }
  }
  if (dias === 0) return new Array(24).fill(0);
  return suma.map((s) => Math.round(s / dias));
}

export function generarSemanaDemo(
  hoyTotal: number,
  hoy: Date
): { dia: string; total: number }[] {
  const diasSem = ["dom", "lun", "mar", "mié", "jue", "vie", "sab"];
  const resultado: { dia: string; total: number }[] = [];
  // demo: fórmula determinista con seno e índice para 7 días terminando en hoy
  for (let i = 6; i >= 0; i--) {
    const fecha = new Date(hoy);
    fecha.setDate(hoy.getDate() - i);
    const idx = 6 - i;
    const factor = 0.7 + 0.3 * Math.sin((idx * Math.PI) / 3 + 0.5);
    const total = Math.round(hoyTotal * factor);
    resultado.push({ dia: diasSem[fecha.getDay()], total });
  }
  return resultado;
}

export function generarHorasPromedioDemo(horas: number[]): number[] {
  // demo: curva promedio determinista cercana a la de hoy, suavizada
  return horas.map((v, h) => {
    const pico = 12 + 4 * Math.sin((h - 12) * (Math.PI / 12));
    const base = Math.max(0, v * 0.85 + pico * 0.15);
    return Math.round(base);
  });
}

export type KpiItem = {
  clave: string;
  etiqueta: string;
  valor: string;
  detalle: string;
  tono: "calma" | "lleno" | "fila" | "personal";
  variacion: number | null;
};

export function kpisDelDia(
  resumen: {
    total_visitors: number;
    peak_hour: number | null;
    avg_queue_seconds: number | null;
    staff_coverage_pct: number | null;
    avg_dwell_seconds: number | null;
  },
  ayerTotal: number,
  semanaPasadaTotal: number
): KpiItem[] {
  const staffCoverage = resumen.staff_coverage_pct ?? 92; // demo:
  const espera = resumen.avg_queue_seconds ?? 180; // demo:
  const permanencia = resumen.avg_dwell_seconds ?? 240; // demo:

  const varVsAyer = variacion(resumen.total_visitors, ayerTotal);
  const varVsSemana = variacion(resumen.total_visitors, semanaPasadaTotal);

  return [
    {
      clave: "visitantes",
      etiqueta: "Visitantes hoy",
      valor: String(resumen.total_visitors),
      detalle: `vs ayer ${varVsAyer !== null ? (varVsAyer >= 0 ? "+" : "") + varVsAyer + "%" : "s/d"} · vs semana pasada ${varVsSemana !== null ? (varVsSemana >= 0 ? "+" : "") + varVsSemana + "%" : "s/d"}`,
      tono: "calma",
      variacion: varVsAyer,
    },
    {
      clave: "hora_pico",
      etiqueta: "Hora pico",
      valor: resumen.peak_hour !== null ? `${resumen.peak_hour}:00` : "—",
      detalle: "Franja de mayor afluencia",
      tono: "lleno",
      variacion: null,
    },
    {
      clave: "espera_fila",
      etiqueta: "Espera media en fila",
      valor: espera < 60 ? "< 1 min" : `${Math.round(espera / 60)} min`,
      detalle: espera >= 240 ? "Supera 4 min: revisar cajas" : "Dentro de objetivo",
      tono: "fila",
      variacion: null,
    },
    {
      clave: "cobertura_personal",
      etiqueta: "% tiempo caja atendida",
      valor: `${staffCoverage}%`,
      detalle: staffCoverage < 80 ? "Por debajo de objetivo (80%)" : "Objetivo cumplido",
      tono: "personal",
      variacion: null,
    },
    {
      clave: "permanencia",
      etiqueta: "Permanencia media",
      valor: permanencia < 60 ? "< 1 min" : `${Math.round(permanencia / 60)} min`,
      detalle: "Tiempo medio en tienda",
      tono: "calma",
      variacion: null,
    },
    {
      clave: "conversion",
      etiqueta: "Conversión estimada",
      valor: "34%", // demo:
      detalle: "Basado en tráfico y tickets (demo)",
      tono: "calma",
      variacion: null,
    },
  ];
}