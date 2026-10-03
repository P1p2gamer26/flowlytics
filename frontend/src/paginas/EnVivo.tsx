import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Marco } from "../componentes/Marco";
import { CAPAS, VideoEnVivo, type CamaraEnVivo, type Capa } from "../componentes/VideoEnVivo";
import { get } from "../api";

export default function EnVivo() {
  const [camaras, setCamaras] = useState<CamaraEnVivo[] | null>(null);
  const [capa, setCapa] = useState<Capa>("normal");

  useEffect(() => {
    const cargar = () => {
      get<CamaraEnVivo[]>("/api/camaras/en_vivo/")
        // key=id en las celdas: los iframes de YouTube no se recargan.
        .then(setCamaras)
        .catch(() => setCamaras((prev) => prev ?? []));
    };
    cargar();
    const reloj = setInterval(cargar, 15_000);
    return () => clearInterval(reloj);
  }, []);

  const selector = (
    <label className="flex items-center gap-2 text-sm">
      Capa para todas
      <select value={capa} onChange={(e) => setCapa(e.target.value as Capa)}
              className="rounded border border-tinta-2/30 bg-panel px-2 py-1.5">
        {CAPAS.map((c) => <option key={c} value={c}>{c[0].toUpperCase() + c.slice(1)}</option>)}
      </select>
    </label>
  );

  return (
    <Marco titulo="En vivo" acciones={selector}>
      {camaras === null && <p className="col-span-12">Cargando cámaras…</p>}
      {camaras?.length === 0 && (
        <p className="col-span-12 rounded border border-dashed border-tinta-2/40 p-10 text-center">
          Todavía no hay cámaras. <Link to="/conectar/">Conecta una cámara</Link> o{" "}
          <Link to="/subir/">carga un video</Link> para empezar.
        </p>
      )}
      {camaras && camaras.length > 0 && (
        <div className="col-span-12 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {camaras.map((c) => <VideoEnVivo key={c.id} camara={c} capaGlobal={capa} />)}
        </div>
      )}
    </Marco>
  );
}
