import { useRef, useEffect, useState } from "react";

type GraficaHorasProps = {
  hoy: number[];
  promedio: number[];
};

export function GraficaHoras({ hoy, promedio }: GraficaHorasProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = svg.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const width = rect.width;
      const index = Math.min(23, Math.max(0, Math.floor((x / width) * 24)));
      setHoverIndex(index);
    };

    const handleMouseLeave = () => setHoverIndex(null);

    svg.addEventListener("mousemove", handleMouseMove);
    svg.addEventListener("mouseleave", handleMouseLeave);
    return () => {
      svg.removeEventListener("mousemove", handleMouseMove);
      svg.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, []);

  const maxVal = Math.max(...hoy, ...promedio, 1);
  const h = (v: number) => 160 - (v / maxVal) * 140;
  const x = (i: number) => 40 + i * (280 / 23);

  const pathHoy = `M${x(0)},${h(hoy[0])} ` + hoy.slice(1).map((v, i) => {
    const cx = (x(i) + x(i + 1)) / 2;
    return `C${cx},${h(hoy[i])} ${cx},${h(v)} ${x(i + 1)},${h(v)}`;
  }).join(" ");

  const pathPromedio = `M${x(0)},${h(promedio[0])} ` + promedio.slice(1).map((v, i) => {
    const cx = (x(i) + x(i + 1)) / 2;
    return `C${cx},${h(promedio[i])} ${cx},${h(v)} ${x(i + 1)},${h(v)}`;
  }).join(" ");

  const areaPath = pathHoy + ` L${x(23)},200 L${x(0)},200 Z`;

  return (
    <figure role="img" aria-label={`Gráfica de visitantes por hora. Pico: ${Math.max(...hoy)} a las ${hoy.indexOf(Math.max(...hoy))}h`}>
      <svg
        ref={svgRef}
        viewBox="0 0 320 200"
        className="w-full h-48"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="grad-calma" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-calma)" stopOpacity="0.35" />
            <stop offset="100%" stopColor="var(--color-calma)" stopOpacity="0" />
          </linearGradient>
        </defs>

        <g strokeWidth="0.5" stroke="var(--color-tinta-2)" opacity="0.3">
          {[0, 6, 12, 18, 23].map((hr) => (
            <line
              key={hr}
              x1={x(hr)}
              y1={20}
              x2={x(hr)}
              y2={180}
              strokeDasharray="4 4"
            />
          ))}
          <line x1={40} y1={180} x2={320} y2={180} />
        </g>

        <path d={areaPath} fill="url(#grad-calma)" />

        <path
          d={pathPromedio}
          fill="none"
          stroke="var(--color-tinta-2)"
          strokeWidth="1.5"
          strokeDasharray="6 4"
          opacity="0.7"
        />

        <path
          d={pathHoy}
          fill="none"
          stroke="var(--color-calma)"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {hoy.map((v, i) => (
          <circle
            key={i}
            cx={x(i)}
            cy={h(v)}
            r={hoverIndex === i ? 5 : 3}
            fill="var(--color-calma)"
            stroke="var(--color-papel)"
            strokeWidth={hoverIndex === i ? 2 : 0}
            opacity={hoverIndex === i || hoverIndex === null ? 1 : 0.4}
            style={{ transition: "r 0.1s, opacity 0.1s" }}
          >
            <title>
              {i}:00 — {v} visitantes (hoy) · {promedio[i]} promedio
            </title>
          </circle>
        ))}
      </svg>
      <div className="flex justify-between text-xs text-tinta-2 mt-2 px-2">
        <span>0h</span>
        <span>6h</span>
        <span>12h</span>
        <span>18h</span>
        <span>23h</span>
      </div>
      <div className="flex items-center gap-4 text-xs text-tinta-2 mt-2">
        <span className="flex items-center gap-1">
          <span className="w-4 h-0.5 bg-calma rounded" /> Hoy
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-0.5 border-t border-tinta-2/50" style={{ borderTopStyle: "dashed" }} /> Promedio
        </span>
      </div>
    </figure>
  );
}