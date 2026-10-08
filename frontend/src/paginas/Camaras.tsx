import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Marco } from "../componentes/Marco";
import { CeldaCamara, claseColumnas } from "../componentes/CeldaCamara";
import { get } from "../api";

type CamaraGrid = { id: number; name: string; es_video: boolean; viva: boolean;
                     analizado: boolean; gente_ahora: number; ultimo_error: string };
type Vista = { image: string; width: number; height: number; video: string | null };

export default function Camaras({ negocio }: { negocio: number }) {
  const [camaras, setCamaras] = useState<CamaraGrid[] | null>(null);
  const [imagenes, setImagenes] = useState<Record<number, string>>({});

  useEffect(() => {
    let cancelado = false;
    get<CamaraGrid[]>(`/api/camaras/grid/?business=${negocio}`).then(async (filas) => {
      if (cancelado) return;
      setCamaras(filas);
      const pares = await Promise.all(
        filas.map(async (c) => {
          const vista = await get<Vista>(`/api/camaras/${c.id}/vista/`).catch(() => null);
          return [c.id, vista?.image] as const;
        })
      );
      if (cancelado) return;
      const mapa: Record<number, string> = {};
      for (const [id, image] of pares) if (image) mapa[id] = image;
      setImagenes(mapa);
    });
    return () => { cancelado = true; };
  }, [negocio]);

  return (
    <Marco titulo="Cámaras">
      {camaras === null && <p className="col-span-12">Cargando…</p>}
      {camaras?.length === 0 && (
        <p className="col-span-12 rounded-3xl bg-panel p-6 text-center">
          Todavía no hay cámaras. <Link to="/conectar/">Conecta una cámara</Link> o{" "}
          <Link to="/subir/">carga un video</Link> para empezar.
        </p>
      )}
      {camaras && camaras.length > 0 && (
        <>
          <div className={`col-span-12 grid gap-3 ${claseColumnas(camaras.length)}`}>
            {camaras.map((c) => (
              <CeldaCamara key={c.id} camara={c} imagen={imagenes[c.id]} />
            ))}
          </div>
          <p className="col-span-12 text-xs text-tinta-2/70">
            El conteo de cada cámara es del último análisis, no en vivo.
          </p>
        </>
      )}
    </Marco>
  );
}
