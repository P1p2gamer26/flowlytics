type BarrasSemanaProps = {
  semana: { dia: string; total: number }[];
  hoyIndex?: number;
};

export function BarrasSemana({ semana, hoyIndex = 6 }: BarrasSemanaProps) {
  const maxTotal = Math.max(...semana.map((d) => d.total), 1);

  return (
    <figure className="rounded-xl bg-panel p-4" role="img" aria-label={`Visitantes últimos 7 días. Hoy: ${semana[hoyIndex]?.total ?? 0}`}>
      <figcaption className="mb-3 font-medium text-tinta">Últimos 7 días</figcaption>
      <div className="flex items-end justify-between h-48 gap-2">
        {semana.map((d, i) => {
          const heightPct = (d.total / maxTotal) * 100;
          const esHoy = i === hoyIndex;
          return (
            <div key={d.dia} className="flex-1 flex flex-col items-center gap-1">
              <span className="text-xs text-tinta-2 order-2">{d.dia}</span>
              <div
                className={`w-full rounded-t transition-all duration-300 ${
                  esHoy ? "bg-calma" : "bg-calma/40"
                }`}
                style={{ height: `${heightPct}%`, minHeight: "4px" }}
                role="img"
                aria-label={`${d.dia}: ${d.total} visitantes${esHoy ? " (hoy)" : ""}`}
              >
                <span
                  className={`block w-full text-center text-xs font-medium ${
                    esHoy ? "text-calma -mt-5" : "text-tinta-2 -mt-4"
                  }`}
                  style={{ transform: "translateY(100%)" }}
                >
                  {d.total}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </figure>
  );
}