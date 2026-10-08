import { describe, expect, it } from "vitest";
import { ACCIONES, AVISOS, PLANTILLAS, aUmbral, deUmbral, frase, fraseRegla, tonoDeEntrega } from "./avisos";

describe("automatizaciones", () => {
  it("la frase une disparador y acción", () => {
    const t = fraseRegla({ tipo_evento: "long_queue", umbral: 240, canal: "webhook",
                           destino: "", accion: "abrir_caja" });
    expect(t).toContain("→ pedir a un empleado que abra la segunda caja");
    expect(t).not.toContain("long_queue");
  });
  it("el tono: azul si la acción es operativa, el del evento si es aviso", () => {
    expect(tonoDeEntrega({ tipo: "long_queue", accion: "abrir_caja" })).toBe("personal");
    expect(tonoDeEntrega({ tipo: "long_queue", accion: "avisar" })).toBe("fila");
  });
  it("toda plantilla usa un tipo y una acción que existen", () => {
    for (const p of PLANTILLAS) {
      expect(AVISOS[p.tipo_evento]).toBeDefined();
      expect(ACCIONES[p.accion]).toBeDefined();
    }
  });
});

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
