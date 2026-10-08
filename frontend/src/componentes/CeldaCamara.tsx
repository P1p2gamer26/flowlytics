import { Link } from "react-router-dom";

export function claseColumnas(n: number): string {
  if (n <= 1) return "grid-cols-1";
  if (n <= 4) return "grid-cols-1 sm:grid-cols-2";
  return "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3";
}

type Camara = {
  id: number; name: string; viva: boolean; analizado: boolean;
  gente_ahora: number;
};

export function CeldaCamara({ camara, imagen }: { camara: Camara; imagen?: string }) {
  return (
    <Link to={`/camaras/${camara.id}/`}
          className="relative block overflow-hidden rounded-3xl bg-panel p-6">
      {imagen
        ? <img src={imagen} alt="" className="w-full aspect-video object-cover bg-noche rounded-xl" />
        : <div className="w-full aspect-video bg-noche rounded-xl" />}
      <div className="absolute inset-x-0 bottom-0 flex items-center justify-between
                      bg-noche/70 px-4 py-2 text-sm text-papel rounded-b-xl">
        <span className="font-semibold">{camara.name}</span>
        {camara.viva
          ? <span>{camara.analizado ? `${camara.gente_ahora} persona${camara.gente_ahora === 1 ? "" : "s"}` : "Sin analizar"}</span>
          : <span className="text-fila-2 font-semibold">Sin señal</span>}
      </div>
    </Link>
  );
}
