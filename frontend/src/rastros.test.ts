import { describe, expect, it } from "vitest";
import { segmentosDeCola, type PuntoRastro } from "./componentes/Rastros";

const PUNTOS: PuntoRastro[] = [
  { t: 0, xy: [0, 10] }, { t: 2, xy: [20, 10] },
  { t: 5, xy: [50, 10] }, { t: 7, xy: [70, 10] },
];

describe("segmentosDeCola", () => {
  it("solo deja los últimos segundos hasta el tiempo actual", () => {
    expect(segmentosDeCola(PUNTOS, 7, 5)).toEqual([
      { desde: [20, 10], hasta: [50, 10], opacidad: 0.6 },
      { desde: [50, 10], hasta: [70, 10], opacidad: 1 },
    ]);
  });

  it("no dibuja un segmento que cruza desde antes de la cola", () => {
    expect(segmentosDeCola(PUNTOS, 5, 2)).toEqual([]);
  });

  it("sin dos puntos visibles no inventa una línea", () => {
    expect(segmentosDeCola(PUNTOS, 0, 5)).toEqual([]);
  });
});
