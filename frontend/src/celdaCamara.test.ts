import { describe, expect, it } from "vitest";
import { claseColumnas } from "./componentes/CeldaCamara";

describe("claseColumnas", () => {
  it("una camara ocupa todo el ancho", () => {
    expect(claseColumnas(1)).toBe("grid-cols-1");
  });
  it("dos o tres camaras van en dos columnas", () => {
    expect(claseColumnas(2)).toBe("grid-cols-1 sm:grid-cols-2");
    expect(claseColumnas(3)).toBe("grid-cols-1 sm:grid-cols-2");
  });
  it("cuatro camaras llenan un 2x2", () => {
    expect(claseColumnas(4)).toBe("grid-cols-1 sm:grid-cols-2");
  });
  it("de cinco en adelante se usan tres columnas", () => {
    expect(claseColumnas(5)).toBe("grid-cols-1 sm:grid-cols-2 lg:grid-cols-3");
    expect(claseColumnas(9)).toBe("grid-cols-1 sm:grid-cols-2 lg:grid-cols-3");
  });
  it("cero camaras no revienta (caso de negocio vacio)", () => {
    expect(claseColumnas(0)).toBe("grid-cols-1");
  });
});
