import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Marco } from "../componentes/Marco";
import { post } from "../api";

type Camara = { id: number; name: string; descripcion: string; contexto: string };

export default function Cargar({ negocio }: { negocio: number }) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [nombre, setNombre] = useState("");
  const [camara, setCamara] = useState<Camara | null>(null);
  const [descripcion, setDescripcion] = useState("");
  const [estado, setEstado] = useState<"listo" | "subiendo" | "mirando">("listo");
  const [error, setError] = useState("");
  const navegar = useNavigate();

  async function subir(evento: React.FormEvent) {
    evento.preventDefault();
    setError("");
    setEstado("subiendo");
    try {
      const cuerpo = new FormData();
      cuerpo.append("business", String(negocio));
      cuerpo.append("name", nombre || archivo?.name || "Video");
      if (archivo) cuerpo.append("archivo", archivo);
      else cuerpo.append("url", url);

      const nueva = await post<Camara>("/api/camaras/subir/", cuerpo);
      setCamara(nueva);
      setEstado("mirando");

      const visto = await post<{ descripcion: string; contexto: string }>(
        `/api/camaras/${nueva.id}/describir/`,
      ).catch(() => ({ descripcion: "", contexto: "general" }));
      setDescripcion(visto.descripcion);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setEstado("listo");
    }
  }

  async function confirmar() {
    if (!camara) return;
    await post(`/api/camaras/${camara.id}/`, { descripcion });
    navegar(`/camaras/${camara.id}/`);
  }

  return (
    <Marco titulo="Cargar video">
      <form onSubmit={subir} className="col-span-12 max-w-[60ch] space-y-6">
        <label
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); setArchivo(e.dataTransfer.files[0] ?? null); }}
          className="block cursor-pointer rounded-3xl bg-panel p-6 border-2 border-dashed border-tinta-2/40 text-center"
        >
          <input type="file" accept="video/*" className="sr-only"
                 onChange={(e) => setArchivo(e.target.files?.[0] ?? null)} />
          {archivo
            ? <span className="font-mono text-sm">{archivo.name}</span>
            : <span>Suelta un video aquí, o haz clic para buscarlo</span>}
        </label>

        <div>
          <label htmlFor="url" className="block text-sm text-tinta-2">
            O pega la dirección de un video de YouTube, Vimeo o un enlace a un mp4
          </label>
          <input id="url" type="url" value={url} onChange={(e) => setUrl(e.target.value)}
                 placeholder="https://…"
                 className="mt-1 w-full rounded-full bg-panel px-4 py-2 ring-1 ring-tinta-2/20 font-mono text-sm" />
        </div>

        <div>
          <label htmlFor="nombre" className="block text-sm text-tinta-2">
            Cómo quieres llamar a esta cámara
          </label>
          <input id="nombre" value={nombre} onChange={(e) => setNombre(e.target.value)}
                 placeholder="Pasillo central"
                 className="mt-1 w-full rounded-full bg-panel px-4 py-2 ring-1 ring-tinta-2/20" />
        </div>

        {error && <p className="text-alerta">{error}</p>}

        {!camara && (
          <button type="submit" disabled={estado !== "listo" || (!archivo && !url)}
                  className="rounded-full bg-marca px-5 py-2.5 font-semibold text-white hover:bg-marca-2 disabled:opacity-40">
            {estado === "subiendo" ? "Subiendo…" : "Subir video"}
          </button>
        )}
      </form>

      {camara && (
        <section className="col-span-12 max-w-[60ch] space-y-4 border-t border-tinta-2/20 pt-6">
          <h2 className="font-display text-xl">Esto es lo que veo</h2>
          <textarea
            value={estado === "mirando" ? "Mirando el video…" : descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
            rows={2}
            placeholder="Escribe qué se ve: dónde es y qué hay en el plano."
            className="w-full rounded-full bg-panel px-4 py-2 ring-1 ring-tinta-2/20" />
          <p className="text-sm text-tinta-2">
            Corrige la frase si hace falta: con ella el sistema propone mejor las zonas.
          </p>
<button type="button" onClick={confirmar}
                  className="rounded-full bg-marca px-5 py-2.5 font-semibold text-white hover:bg-marca-2">
                Continuar a las zonas
              </button>
        </section>
      )}
    </Marco>
  );
}
