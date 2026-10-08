import { describe, it, expect } from "vitest";
import {
  variacion,
  recomendacionesParaMostrar,
  generarSemanaDemo,
  kpisDelDia,
  RECOMENDACIONES_DEMO,
} from "./panelDatos";

describe("panelDatos", () => {
  describe("variacion", () => {
    it("calcula porcentaje redondeado cuando previo > 0", () => {
      expect(variacion(110, 100)).toBe(10);
      expect(variacion(90, 100)).toBe(-10);
      expect(variacion(105, 100)).toBe(5);
      expect(variacion(95, 100)).toBe(-5);
    });

    it("devuelve null cuando previo <= 0", () => {
      expect(variacion(100, 0)).toBeNull();
      expect(variacion(100, -10)).toBeNull();
    });
  });

  describe("recomendacionesParaMostrar", () => {
    it("incluye recomendación real + 3 demo cuando hay texto real", () => {
      const real = "Abrir una caja extra a las 14:00";
      const result = recomendacionesParaMostrar(real);
      expect(result).toHaveLength(4);
      expect(result[0].id).toBe("real");
      expect(result[0].zona).toBe("General");
      expect(result[0].texto).toBe(real);
      expect(result[0].prioridad).toBe("media");
      expect(result.slice(1)).toEqual(RECOMENDACIONES_DEMO.slice(0, 3));
    });

    it("devuelve todas las demo cuando no hay texto real", () => {
      expect(recomendacionesParaMostrar(undefined)).toEqual(RECOMENDACIONES_DEMO);
      expect(recomendacionesParaMostrar("")).toEqual(RECOMENDACIONES_DEMO);
      expect(recomendacionesParaMostrar("   ")).toEqual(RECOMENDACIONES_DEMO);
    });
  });

  describe("generarSemanaDemo", () => {
    it("devuelve 7 elementos con días correctos", () => {
      const hoy = new Date(2026, 9, 8); // jueves
      const semana = generarSemanaDemo(1000, hoy);
      expect(semana).toHaveLength(7);
      expect(semana.map((d) => d.dia)).toEqual(["vie", "sab", "dom", "lun", "mar", "mié", "jue"]);
    });

    it("es determinista: misma entrada produce misma salida", () => {
      const hoy = new Date(2026, 9, 8);
      const s1 = generarSemanaDemo(1000, hoy);
      const s2 = generarSemanaDemo(1000, hoy);
      expect(s1).toEqual(s2);
    });

    it("totales son números positivos", () => {
      const hoy = new Date(2026, 9, 8);
      const semana = generarSemanaDemo(500, hoy);
      for (const d of semana) {
        expect(d.total).toBeGreaterThan(0);
      }
    });
  });

  describe("kpisDelDia", () => {
    it("devuelve 6 KPIs con estructura correcta", () => {
      const resumen = {
        total_visitors: 1000,
        peak_hour: 14,
        avg_queue_seconds: 180,
        staff_coverage_pct: 92,
        avg_dwell_seconds: 240,
      };
      const kpis = kpisDelDia(resumen, 900, 850);
      expect(kpis).toHaveLength(6);

      const claves = kpis.map((k) => k.clave);
      expect(claves).toEqual([
        "visitantes",
        "hora_pico",
        "espera_fila",
        "cobertura_personal",
        "permanencia",
        "conversion",
      ]);
    });

    it("usa valores demo cuando resumen tiene null y marca tono correcto", () => {
      const resumen = {
        total_visitors: 1000,
        peak_hour: null,
        avg_queue_seconds: null,
        staff_coverage_pct: null,
        avg_dwell_seconds: null,
      };
      const kpis = kpisDelDia(resumen, 900, 850);

      expect(kpis.find((k) => k.clave === "hora_pico")?.valor).toBe("—");
      expect(kpis.find((k) => k.clave === "cobertura_personal")?.valor).toBe("92%");
      expect(kpis.find((k) => k.clave === "espera_fila")?.valor).toBe("3 min");
      expect(kpis.find((k) => k.clave === "permanencia")?.valor).toBe("4 min");
      expect(kpis.find((k) => k.clave === "conversion")?.valor).toBe("34%");
    });

    it("tono fila para espera >= 240s", () => {
      const resumen = {
        total_visitors: 1000,
        peak_hour: 14,
        avg_queue_seconds: 300,
        staff_coverage_pct: 92,
        avg_dwell_seconds: 240,
      };
      const kpis = kpisDelDia(resumen, 900, 850);
      expect(kpis.find((k) => k.clave === "espera_fila")?.tono).toBe("fila");
    });

    it("variacion en KPI visitantes usa ayer", () => {
      const resumen = {
        total_visitors: 1100,
        peak_hour: 14,
        avg_queue_seconds: 180,
        staff_coverage_pct: 92,
        avg_dwell_seconds: 240,
      };
      const kpis = kpisDelDia(resumen, 1000, 850);
      const kpiVis = kpis.find((k) => k.clave === "visitantes");
      expect(kpiVis?.variacion).toBe(10);
      expect(kpiVis?.detalle).toContain("+10%");
    });
  });
});