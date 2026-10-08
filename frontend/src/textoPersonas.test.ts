import { describe, expect, it } from "vitest";
import { textoPersonas } from "./componentes/VideoEnVivo";

describe("textoPersonas", () => {
  it("con roles muestra clientes y trabajadores", () => {
    expect(textoPersonas({ gente_ahora: 3, clientes: 2, trabajadores: 1 })).toBe("2 clientes · 1 trabajador");
  });
  it("sin roles cae al total", () => {
    expect(textoPersonas({ gente_ahora: 1, clientes: null, trabajadores: null })).toBe("1 persona");
    expect(textoPersonas({ gente_ahora: 4 })).toBe("4 personas");
  });
});
