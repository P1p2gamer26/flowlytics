import { describe, expect, it } from "vitest";
import { colorDeCalor } from "./componentes/MapaCalor";

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
