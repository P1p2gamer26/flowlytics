import { useEffect, useState } from "react";
import type { Recomendacion } from "../panelDatos";

type RecomendacionesIAProps = {
  recomendaciones: Recomendacion[];
};

export function RecomendacionesIA({ recomendaciones }: RecomendacionesIAProps) {
  const [visibleCount, setVisibleCount] = useState(0);
  const [typingDone, setTypingDone] = useState(false);
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    mq.addEventListener?.("change", handler);
    return () => mq.removeEventListener?.("change", handler);
  }, []);

  useEffect(() => {
    if (reduceMotion) {
      setVisibleCount(recomendaciones.length);
      setTypingDone(true);
      return;
    }

    setVisibleCount(0);
    setTypingDone(false);

    const timer = setInterval(() => {
      setVisibleCount((prev) => {
        if (prev >= recomendaciones.length) {
          clearInterval(timer);
          setTypingDone(true);
          return prev;
        }
        return prev + 1;
      });
    }, 450);

    return () => clearInterval(timer);
  }, [recomendaciones.length, reduceMotion]);

  const prioridadColor = (p: Recomendacion["prioridad"]) =>
    p === "alta"
      ? "bg-fila/15 text-fila"
      : p === "media"
      ? "bg-lleno/15 text-lleno"
      : "bg-calma/15 text-calma";

  return (
    <section className="rounded-3xl bg-panel p-6" aria-label="Recomendaciones de Flowlytics IA">
      <header className="rounded-3xl bg-marca text-white p-4 mb-4">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white">
            <img src={import.meta.env.BASE_URL + "logo.png"} alt="" className="h-7 w-7" />
          </span>
          <div>
            <h2 className="font-display text-lg font-bold">Flowlytics IA</h2>
            <p className="text-xs text-white/80 flex items-center gap-1.5">
              <span
                className={`w-1.5 h-1.5 rounded-full bg-white/30 animate-pulse ${
                  reduceMotion ? "animate-none" : ""
                }`}
              />
              Analizando tu tienda
            </p>
          </div>
        </div>
      </header>

      <ul className="space-y-3" role="list">
        {recomendaciones.slice(0, visibleCount).map((rec, idx) => (
          <li
            key={rec.id}
            className={`relative rounded-3xl bg-panel p-4 transition-all duration-500 ${
              reduceMotion
                ? "opacity-100 translate-y-0"
                : idx < visibleCount - 1
                ? "opacity-100 translate-y-0"
                : idx === visibleCount - 1 && !typingDone
                ? "opacity-100 translate-y-0"
                : "opacity-0 translate-y-2"
            }`}
            style={{
              animationDelay: reduceMotion ? "0ms" : `${idx * 450}ms`,
            }}
          >
            <div className="flex flex-wrap items-start gap-3">
              <span
                className={`shrink-0 px-2 py-0.5 rounded text-xs font-medium ${prioridadColor(
                  rec.prioridad
                )}`}
              >
                {rec.prioridad}
              </span>
              <span className="text-xs text-tinta-2 font-medium">{rec.zona}</span>
            </div>
            <p
              className="mt-2 text-sm leading-relaxed text-tinta"
              style={{
                opacity: reduceMotion || typingDone || idx < visibleCount - 1 ? 1 : 0,
                animation: reduceMotion || typingDone ? "none" : "typing 1.2s steps(40, end) forwards",
              }}
            >
              {rec.texto}
            </p>
            <div className="mt-2 flex flex-wrap gap-2 text-xs text-tinta-2">
              <span className="flex items-center gap-1">
                <span className="font-medium text-tinta">Dato:</span>
                {rec.dato}
              </span>
              {rec.impacto && (
                <span className="flex items-center gap-1">
                  <span className="font-medium text-calma">Impacto:</span>
                  {rec.impacto}
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>

      <style>{`
        @keyframes typing {
          from { width: 0; }
          to { width: 100%; }
        }
      `}</style>
    </section>
  );
}