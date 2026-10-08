type BarrasSemanaProps = {
  semana: { dia: string; total: number }[];
  hoyIndex?: number;
};

// La barra crece dentro de una caja de alto fijo: un % de alto dentro de una columna
// flex sin alto propio se resolvía a 0 y todas las barras salían planas.
export function BarrasSemana({ semana, hoyIndex = 6 }: BarrasSemanaProps) {
  const maxTotal = Math.max(...semana.map((d) => d.total), 1);

  return (
    <figure role="img" aria-label={`Visitantes últimos 7 días. Hoy: ${semana[hoyIndex]?.total ?? 0}`}>
      <div className="flex h-52 items-stretch gap-2">
        {semana.map((d, i) => {
          const esHoy = i === hoyIndex;
          return (
            <div key={d.dia} className="flex flex-1 flex-col items-center gap-1.5">
              <div className="flex w-full flex-1 flex-col justify-end">
                <span className={`mb-1 text-center text-xs font-semibold ${esHoy ? "text-marca" : "text-tinta-2"}`}>
                  {d.total}
                </span>
                <div className={`w-full rounded-xl ${esHoy ? "bg-marca" : "bg-marca-suave"}`}
                     style={{ height: `${Math.max(4, (d.total / maxTotal) * 100)}%` }} />
              </div>
              <span className={`text-xs ${esHoy ? "font-semibold text-tinta" : "text-tinta-2"}`}>{d.dia}</span>
            </div>
          );
        })}
      </div>
    </figure>
  );
}
