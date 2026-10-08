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
          className="rounded-3xl bg-panel p-6"
        >
          <p className="text-xs font-medium text-tinta-2 tracking-wide uppercase">
            {kpi.etiqueta}
          </p>
          <p className="mt-1 font-display text-3xl md:text-4xl font-extrabold text-acento tabular-nums">
            {kpi.valor}
          </p>
          <p className="mt-2 text-xs text-tinta-2 max-w-xs">{kpi.detalle}</p>
          {kpi.variacion !== null && (
            <div className="mt-3 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold">
              <span className={kpi.variacion >= 0 ? "text-calma" : "text-fila"}>
                {kpi.variacion >= 0 ? "▲" : "▼"}
              </span>
              <span className={kpi.variacion >= 0 ? "text-calma" : "text-fila"}>
                {Math.abs(kpi.variacion)}%
              </span>
            </div>
          )}
        </article>
      ))}
    </div>
  );
}