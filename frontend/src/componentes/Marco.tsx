import { NavLink } from "react-router-dom";
import type { ReactNode } from "react";

const RUTAS = [
  { a: "/", texto: "En vivo", icon: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="w-5 h-5">
      <circle cx="12" cy="12" r="2" />
      <path d="M16.24 7.76a6 6 0 0 1 0 8.49M7.76 16.24a6 6 0 0 1 0-8.49M19.07 4.93a10 10 0 0 1 0 14.14M4.93 19.07a10 10 0 0 1 0-14.14" />
    </svg>
  )},
  { a: "/panel/", texto: "Panel", icon: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="w-5 h-5">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  )},
  { a: "/camaras/", texto: "Cámaras", icon: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="w-5 h-5">
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
      <circle cx="12" cy="13" r="4" />
    </svg>
  )},
  { a: "/avisos/", texto: "Avisos", icon: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="w-5 h-5">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  )},
  { a: "/conectar/", texto: "Conectar cámara", icon: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="w-5 h-5">
      <rect x="2" y="3" width="20" height="14" rx="2" />
      <path d="M8 21h8" />
      <path d="M12 17v4" />
    </svg>
  )},
  { a: "/subir/", texto: "Cargar video", icon: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="w-5 h-5">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  )},
];

export function Marco({ titulo, subtitulo, acciones, children }: {
  titulo: string;
  subtitulo?: string;
  acciones?: ReactNode;
  children: ReactNode;
}) {
  const fechaHoy = new Date().toLocaleDateString("es", { weekday: "short", day: "numeric", month: "short" });

  return (
    <div className="min-h-screen bg-papel">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[15rem] flex-col bg-noche text-white md:flex" aria-label="Principal">
        <div className="flex items-center gap-3 px-4 py-6 border-b border-white/10">
          <img src={import.meta.env.BASE_URL + "logo.png"} alt="" width="32" height="32" />
          <span className="font-display font-extrabold text-lg">Flowlytics</span>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1" aria-label="Navegación principal">
          {RUTAS.map((r) => (
            <NavLink
              key={r.a}
              to={r.a}
              end={r.a === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-marca text-white"
                    : "text-white/70 hover:bg-white/10"
                }`}
            >
              <span aria-hidden="true">{r.icon}</span>
              {r.texto}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-white/10 p-4">
          <p className="text-xs text-white/50 text-center">
            Sin reconocimiento facial · Sin video continuo
          </p>
        </div>
      </aside>

      <header className="md:ml-[15rem]">
        <nav className="md:hidden bg-noche px-4 py-3 overflow-x-auto" aria-label="Navegación móvil">
          <div className="flex items-center gap-3 whitespace-nowrap">
            <img src={import.meta.env.BASE_URL + "logo.png"} alt="" width="28" height="28" className="shrink-0" />
            <span className="font-display font-extrabold text-white shrink-0">Flowlytics</span>
            <span className="w-px h-6 bg-white/20 shrink-0" aria-hidden="true" />
            {RUTAS.map((r) => (
              <NavLink
                key={r.a}
                to={r.a}
                end={r.a === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium shrink-0 transition-colors ${
                    isActive
                      ? "bg-marca text-white"
                      : "text-white/70 hover:bg-white/10"
                  }`}
              >
                <span aria-hidden="true">{r.icon}</span>
                <span className="hidden sm:inline">{r.texto}</span>
              </NavLink>
            ))}
          </div>
        </nav>
        <div className="bg-panel rounded-2xl m-4 md:m-4 px-6 py-3 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex-1">
            <h1 className="font-display text-tinta font-extrabold text-2xl tracking-tight">
              {titulo}
              {subtitulo && (
                <span className="ml-2 font-sans text-base font-normal text-tinta-2">
                  {subtitulo}
                </span>
              )}
            </h1>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            {acciones}
            <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-tinta-2/10 text-tinta-2 text-sm font-medium">
              {fechaHoy}
            </span>
          </div>
        </div>

      </header>

      <main className="md:ml-[15rem] grid grid-cols-12 gap-6 px-4 md:px-6 pb-8">
        {children}
      </main>
    </div>
  );
}