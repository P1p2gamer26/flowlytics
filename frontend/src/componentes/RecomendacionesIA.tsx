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
      ? "bg-fila text-fila"
      : p === "media"
      ? "bg-lleno text-lleno"
      : "bg-calma text-calma";

  return (
    <section className="rounded-xl bg-noche p-5 text-papel" aria-label="Recomendaciones de Flowlytics IA">
      <header className="flex items-center gap-3 mb-4">
        <img src="/favicon.svg" alt="" className="h-7 w-7" />
        <div>
          <h2 className="font-display text-lg font-bold">Recomendaciones de Flowlytics IA</h2>
          <p className="text-xs text-papel/70 flex items-center gap-1.5">
            <span
              className={`w-1.5 h-1.5 rounded-full bg-calma animate-pulse ${
                reduceMotion ? "animate-none" : ""
              }`}
            />
            Analizando tu tienda
          </p>
        </div>
      </header>

      <ul className="space-y-3" role="list">
        {recomendaciones.slice(0, visibleCount).map((rec, idx) => (
          <li
            key={rec.id}
            className={`relative rounded-lg bg-noche/50 p-4 border border-papel/10 transition-all duration-500 ${
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
              <span className="text-xs text-papel/60 font-medium">{rec.zona}</span>
            </div>
            <p
              className="mt-2 text-sm leading-relaxed"
              style={{
                opacity: reduceMotion || typingDone || idx < visibleCount - 1 ? 1 : 0,
                animation: reduceMotion || typingDone ? "none" : "typing 1.2s steps(40, end) forwards",
              }}
            >
              {rec.texto}
            </p>
            <div className="mt-2 flex flex-wrap gap-2 text-xs text-papel/70">
              <span className="flex items-center gap-1">
                <span className="font-medium text-papel">Dato:</span>
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