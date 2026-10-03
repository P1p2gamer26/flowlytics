import { describe, expect, it } from "vitest";
import { aEscala, normalEntrada } from "./geometria";

describe("aEscala", () => {
  it("deja el punto igual cuando el canvas se muestra a tamaño real", () => {
    expect(aEscala([10, 20], { mostrado: [640, 480], real: [640, 480] })).toEqual([10, 20]);
  });

  it("escala cuando el canvas se muestra a la mitad", () => {
    expect(aEscala([10, 20], { mostrado: [320, 240], real: [640, 480] })).toEqual([20, 40]);
  });

  it("redondea a entero: el polígono se guarda en píxeles del frame", () => {
    expect(aEscala([10, 10], { mostrado: [300, 300], real: [640, 480] })).toEqual([21, 16]);
  });
});

describe("normalEntrada", () => {
  it("una línea horizontal A→B hacia la derecha entra hacia arriba", () => {
    expect(normalEntrada([[50, 100], [150, 100]])).toEqual([0, -1]);
  });

  it("invertir le da la vuelta", () => {
    expect(normalEntrada([[50, 100], [150, 100]], true)).toEqual([-0, 1]);
  });

  it("es unitaria: la flecha mide lo mismo dibujes la línea larga o corta", () => {
    const [x, y] = normalEntrada([[0, 0], [30, 40]]);
    expect(Math.hypot(x, y)).toBeCloseTo(1);
  });

  it("una línea de longitud cero no revienta ni devuelve NaN", () => {
    expect(normalEntrada([[10, 10], [10, 10]])).toEqual([0, 0]);
  });
});

