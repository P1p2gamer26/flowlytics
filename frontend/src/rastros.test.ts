import { describe, expect, it } from "vitest";
import { segmentosDeCola, estela, type PuntoRastro } from "./componentes/Rastros";

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

describe("estela", () => {
  it("menos de 2 puntos devuelve array vacío", () => {
    expect(estela([])).toEqual([]);
    expect(estela([[10, 20]])).toEqual([]);
  });
  it("dos puntos devuelve un segmento", () => {
    const r = estela([[0, 0], [10, 10]]);
    expect(r).toHaveLength(1);
    expect(r[0].desde).toEqual([0, 0]);
    expect(r[0].hasta).toEqual([10, 10]);
    expect(r[0].opacidad).toBe(1);
    expect(r[0].grosor).toBe(4);
  });
  it("opacidad y grosor crecen hacia la cabeza", () => {
    const r = estela([[0, 0], [10, 10], [20, 20], [30, 30]]);
    expect(r).toHaveLength(3);
    expect(r[0].opacidad).toBeLessThan(r[1].opacidad);
    expect(r[1].opacidad).toBeLessThan(r[2].opacidad);
    expect(r[0].grosor).toBeLessThan(r[1].grosor);
    expect(r[1].grosor).toBeLessThan(r[2].grosor);
  });
  it("respeta n: solo usa los últimos n puntos", () => {
    const puntos: [number, number][] = [[0, 0], [10, 10], [20, 20], [30, 30], [40, 40], [50, 50], [60, 60]];
    const r = estela(puntos, 4);
    expect(r).toHaveLength(3);
  });
  it("segmentos conectados: hasta del anterior === desde del siguiente", () => {
    const r = estela([[0, 0], [10, 10], [20, 20]]);
    expect(r[0].hasta).toEqual(r[1].desde);
  });
});