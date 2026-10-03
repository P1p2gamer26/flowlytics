import { describe, expect, it } from "vitest";

export const formatearResumen = (metrica: string, valor: number): string => {
  if (metrica === "fila_caja") return `Fila en caja: ${Math.round(valor / 60)} min`;
  if (metrica === "permanencia_mesa") return `Permanencia media: ${Math.round(valor / 60)} min`;
  if (metrica === "cola_mostrador") return `Cola en mostrador: ${Math.round(valor / 60)} min`;
  if (metrica === "rotacion") return `Rotación hoy: ${valor} personas`;
  return `${metrica}: ${valor}`;
};

describe("resumen de negocio", () => {
  it("formatea fila_caja en texto entendible", () => {
    expect(formatearResumen("fila_caja", 300)).toBe("Fila en caja: 5 min");
  });
});
