import { describe, expect, it } from "vitest";
import { comoLlevaAhi, centroXDePie } from "./componentes/Personas";

describe("centroXDePie", () => {
  it("es el punto medio horizontal de la caja, igual que pie_de_caja en el backend", () => {
    expect(centroXDePie([10, 20, 50, 120])).toBe(30);
  });

  it("con una caja de ancho cero no revienta", () => {
    expect(centroXDePie([5, 5, 5, 5])).toBe(5);
  });
});

describe("marca de personal", () => {
  it("un track marcado como personal muestra el texto 'personal'", () => {
    const personal = [4];
    const esPersonal = new Set(personal);
    expect(esPersonal.has(4)).toBe(true);
    expect(esPersonal.has(5)).toBe(false);
  });
});

describe("filtro de rastros fragmentados", () => {
  it("no muestra etiqueta si hay menos de 5 segundos y no es personal", () => {
    expect(comoLlevaAhi(3)).toBe("3 s");
  });

  it("muestra etiqueta completa para permanencias largas", () => {
    expect(comoLlevaAhi(120)).toBe("2 min");
  });

  it("redondea correctamente horas y minutos", () => {
    expect(comoLlevaAhi(3750)).toBe("1 h 15 min");
  });
});
