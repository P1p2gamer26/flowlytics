const TONOS = { normal: "text-tinta", alerta: "text-alerta", ok: "text-ok" } as const;

export function Cifra({ valor, etiqueta, tono = "normal" }: {
  valor: string | number;
  etiqueta: string;
  tono?: keyof typeof TONOS;
}) {
  return (
    <div className="border-l border-tinta-2/25 pl-4 first:border-l-0 first:pl-0">
      <div className={`font-display text-cifra font-semibold tabular-nums ${TONOS[tono]}`}>
        {valor}
      </div>
      <div className="text-sm text-tinta-2">{etiqueta}</div>
    </div>
  );
}
