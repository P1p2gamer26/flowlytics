import { describe, expect, it } from "vitest";
import { AVISOS, aUmbral, deUmbral, frase } from "./avisos";

describe("unidades", () => {
  it("la espera se pregunta en minutos y se guarda en segundos", () => {
    expect(aUmbral("long_queue", 5)).toBe(300);
    expect(deUmbral("long_queue", 300)).toBe(5);
  });
  it("las personas se guardan tal cual", () => {
    expect(aUmbral("crowded_queue", 4)).toBe(4);
    expect(deUmbral("crowded_queue", 4)).toBe(4);
  });
});

describe("frase", () => {
  it("dice cuándo y a dónde, sin una sola clave del sistema", () => {
    const texto = frase({ tipo_evento: "long_queue", umbral: 300,
                          canal: "email", destino: "dueno@tienda.co" });

    expect(texto).toBe(
      "Te avisamos si alguien espera más de 5 min en la fila, por correo a dueno@tienda.co.");
    expect(texto).not.toContain("long_queue");
  });

  it("la fila con gente se cuenta en personas", () => {
    expect(frase({ tipo_evento: "crowded_queue", umbral: 4,
                   canal: "email", destino: "d@t.co" }))
      .toContain("si hay más de 4 personas en la fila");
  });

  it("la caja desatendida no lleva número", () => {
    expect(frase({ tipo_evento: "empty_counter", umbral: 1,
                   canal: "webhook", destino: "https://x/y" }))
      .toBe("Te avisamos si la caja se queda sin nadie atendiendo, al webhook configurado.");
  });

  it("todos los tipos tienen título y unidad", () => {
    for (const tipo of Object.keys(AVISOS) as (keyof typeof AVISOS)[]) {
      expect(AVISOS[tipo].titulo.length).toBeGreaterThan(3);
      expect(["minutos", "personas"]).toContain(AVISOS[tipo].unidad);
    }
  });
});
