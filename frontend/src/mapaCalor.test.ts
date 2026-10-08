import { describe, expect, it } from "vitest";
import { colorDeCalor, colorCelda } from "./componentes/MapaCalor";

describe("colorDeCalor", () => {
  it("en 0 es el verde de calma", () => {
    expect(colorDeCalor(0)).toBe("#0f7a57");
  });
  it("en 1 es el rojo de fila", () => {
    expect(colorDeCalor(1)).toBe("#d6432c");
  });
  it("a mitad de camino pasa por el ambar de lleno", () => {
    expect(colorDeCalor(0.5)).toBe("#e9a13b");
  });
  it("valores fuera de rango se recortan a 0..1", () => {
    expect(colorDeCalor(-1)).toBe(colorDeCalor(0));
    expect(colorDeCalor(5)).toBe(colorDeCalor(1));
  });
});

describe("colorCelda", () => {
  it("valor < 0.05 devuelve alfa 0 (transparente)", () => {
    expect(colorCelda(0.04)[3]).toBe(0);
    expect(colorCelda(0)[3]).toBe(0);
  });
  it("valor 0.05 tiene alfa > 0", () => {
    expect(colorCelda(0.05)[3]).toBeGreaterThan(0);
  });
  it("alfa crece con el valor y se limita a 255", () => {
    expect(colorCelda(0.1)[3]).toBeLessThan(colorCelda(0.5)[3]);
    expect(colorCelda(1)[3]).toBe(255);
    expect(colorCelda(2)[3]).toBe(255);
  });
  it("rgb coincide con colorDeCalor", () => {
    const c = colorCelda(0.5);
    expect(c[0]).toBe(0xe9);
    expect(c[1]).toBe(0xa1);
    expect(c[2]).toBe(0x3b);
  });
  it("componentes en rango 0..255", () => {
    for (const v of [0, 0.1, 0.5, 1, 2]) {
      const [r, g, b, a] = colorCelda(v);
      expect(r).toBeGreaterThanOrEqual(0);
      expect(r).toBeLessThanOrEqual(255);
      expect(g).toBeGreaterThanOrEqual(0);
      expect(g).toBeLessThanOrEqual(255);
      expect(b).toBeGreaterThanOrEqual(0);
      expect(b).toBeLessThanOrEqual(255);
      expect(a).toBeGreaterThanOrEqual(0);
      expect(a).toBeLessThanOrEqual(255);
    }
  });
});