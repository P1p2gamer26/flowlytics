import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Marco } from "../componentes/Marco";
import { post } from "../api";

type Camara = { id: number };
type Prueba = { ok: boolean; mensaje: string };

export default function Conectar({ negocio }: { negocio: number }) {
  const [nombre, setNombre] = useState("");
  const [source, setSource] = useState("");
  const [usuario, setUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [prueba, setPrueba] = useState<Prueba | null>(null);
  const [probando, setProbando] = useState(false);
  const [error, setError] = useState("");
  const navegar = useNavigate();

  async function probar() {
    setError("");
    setPrueba(null);
    setProbando(true);
    try {
      setPrueba(await post<Prueba>("/api/camaras/probar/",
                                   { business: negocio, source, usuario, password }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setProbando(false);
    }
  }

  async function guardar() {
    setError("");
    try {
      const cam = await post<Camara>("/api/camaras/", {
        business: negocio, name: nombre || "Cámara", source, usuario, password,
      });
      navegar(`/camaras/${cam.id}/`);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <Marco titulo="Conectar una cámara">
      <div className="col-span-12 max-w-[60ch] space-y-6">
        <p className="text-tinta-2">
          Necesitas la dirección del video de la cámara. Está en su manual o en su
          aplicación, y se parece a <code>rtsp://192.168.1.50:554/stream1</code>. La
          cámara tiene que estar en la misma red que este servidor.
        </p>

        <div>
          <label htmlFor="nombre" className="block text-sm text-tinta-2">
            Cómo quieres llamarla
          </label>
          <input id="nombre" value={nombre} onChange={(e) => setNombre(e.target.value)}
                 placeholder="Puerta principal"
                 className="mt-1 w-full rounded border border-tinta-2/30 bg-panel px-3 py-2" />
        </div>

        <div>
          <label htmlFor="source" className="block text-sm text-tinta-2">
            Dirección del video
          </label>
          <input id="source" value={source} onChange={(e) => setSource(e.target.value)}
                 placeholder="rtsp://192.168.1.50:554/stream1"
                 className="mt-1 w-full rounded border border-tinta-2/30 bg-panel px-3 py-2 font-mono text-sm" />
        </div>

        <div className="flex gap-3">
          <div className="flex-1">
            <label htmlFor="usuario" className="block text-sm text-tinta-2">
              Usuario de la cámara
            </label>
            <input id="usuario" value={usuario} onChange={(e) => setUsuario(e.target.value)}
                   autoComplete="off"
                   className="mt-1 w-full rounded border border-tinta-2/30 bg-panel px-3 py-2" />
          </div>
          <div className="flex-1">
            <label htmlFor="password" className="block text-sm text-tinta-2">
              Contraseña
            </label>
            <input id="password" type="password" value={password}
                   autoComplete="new-password"
                   onChange={(e) => setPassword(e.target.value)}
                   className="mt-1 w-full rounded border border-tinta-2/30 bg-panel px-3 py-2" />
          </div>
        </div>
        <p className="text-sm text-tinta-2">
          La contraseña se guarda cifrada y no se vuelve a mostrar. Si algún día la
          cambias en la cámara, la escribes otra vez aquí.
        </p>

        <div className="flex flex-wrap items-center gap-3">
          <button type="button" onClick={probar} disabled={!source || probando}
                  className="rounded border border-tinta-2/40 px-4 py-2 disabled:opacity-40">
            {probando ? "Probando…" : "Probar conexión"}
          </button>
          <button type="button" onClick={guardar} disabled={!source}
                  className="rounded bg-zona px-5 py-2.5 text-white disabled:opacity-40">
            Guardar cámara
          </button>
        </div>

        {prueba && (
          <p aria-live="polite"
             className={prueba.ok ? "text-ok" : "text-alerta"}>{prueba.mensaje}</p>
        )}
        {error && <p className="text-alerta">{error}</p>}
      </div>
    </Marco>
  );
}
