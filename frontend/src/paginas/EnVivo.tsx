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

  const personasAhora = (camaras ?? [])
    .filter((c) => c.viva)
    .reduce((total, c) => total + c.gente_ahora, 0);

  const selector = (
    <div className="flex flex-wrap items-center gap-4 text-sm">
      <span className="flex items-center gap-2 rounded-full bg-panel px-4 py-1.5">
        <span className="latido h-2 w-2 rounded-full bg-fila" aria-hidden="true" />
        <span className="font-display font-bold tracking-wide">EN VIVO</span>
        <span className="text-tinta-2">· {personasAhora} personas ahora</span>
      </span>

      <div className="flex overflow-hidden rounded-full bg-panel p-1"
           role="group" aria-label="Capa para todas">
        {CAPAS.map((c) => (
          <button key={c} type="button" onClick={() => setCapa(c)} aria-pressed={capa === c}
                  className={`rounded-full px-3 py-1 text-xs ${
                    capa === c ? "bg-marca text-white" : "text-tinta-2 hover:text-tinta"
                  }`}>
            {c[0].toUpperCase() + c.slice(1)}
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <Marco titulo="En vivo" acciones={selector}>
      {camaras === null && <p className="col-span-12">Cargando cámaras…</p>}
      {camaras?.length === 0 && (
        <p className="col-span-12 rounded-3xl bg-panel p-10 text-center">
          Todavía no hay cámaras. <Link to="/conectar/">Conecta una cámara</Link> o{" "}
          <Link to="/subir/">carga un video</Link> para empezar.
        </p>
      )}
      {camaras && camaras.length > 0 && (
        <div className="col-span-12 grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
          {camaras.map((c) => <VideoEnVivo key={c.id} camara={c} capaGlobal={capa} />)}
        </div>
      )}
    </Marco>
  );
}
