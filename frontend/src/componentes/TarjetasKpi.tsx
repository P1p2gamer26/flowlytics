import type { KpiItem } from "../panelDatos";

type TarjetasKpiProps = {
  kpis: KpiItem[];
};

export function TarjetasKpi({ kpis }: TarjetasKpiProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {kpis.map((kpi) => (
        <article
          key={kpi.clave}
          className={`relative rounded-xl bg-panel shadow-sm border-t-4 transition-all ${
            kpi.tono === "calma"
              ? "border-calma"
              : kpi.tono === "lleno"
              ? "border-lleno"
              : kpi.tono === "fila"
              ? "border-fila"
              : "border-personal"
          }`}
        >
          <div className="p-4">
            <p className="text-xs font-medium text-tinta-2 tracking-wide uppercase">
              {kpi.etiqueta}
            </p>
            <p className="mt-1 font-display text-3xl md:text-4xl font-bold text-tinta tabular-nums">
              {kpi.valor}
            </p>
            <p className="mt-2 text-xs text-tinta-2 max-w-xs">{kpi.detalle}</p>
          </div>
          {kpi.variacion !== null && (
            <div
              className={`absolute top-3 right-3 px-2 py-0.5 rounded-full text-xs font-semibold ${
                kpi.variacion >= 0
                  ? "bg-calma/15 text-calma"
                  : "bg-fila/15 text-fila"
              }`}
            >
              {kpi.variacion >= 0 ? "▲" : "▼"} {Math.abs(kpi.variacion)}%
            </div>
          )}
        </article>
      ))}
    </div>
  );
}