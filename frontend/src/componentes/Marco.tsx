import { Link, NavLink } from "react-router-dom";
import type { ReactNode } from "react";

const RUTAS = [
  { a: "/", texto: "En vivo" },
  { a: "/panel/", texto: "Panel" },
  { a: "/camaras/", texto: "Cámaras" },
  { a: "/avisos/", texto: "Avisos" },
  { a: "/conectar/", texto: "Conectar cámara" },
  { a: "/subir/", texto: "Cargar video" },
];

export function Marco({ titulo, subtitulo, acciones, children }: {
  titulo: string;
  subtitulo?: string;
  acciones?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen">
      <header className="rounded-b-3xl bg-panel">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center gap-x-8 gap-y-3
                        px-6 py-4">
          <Link to="/" className="flex items-center gap-2 font-display font-extrabold text-marca"
                aria-label="Flowlytics - Inicio">
            <img src={import.meta.env.BASE_URL + "logo.png"} alt="" width="32" height="32" />
            Flowlytics
          </Link>
          <span className="w-px h-8 bg-tinta-2/20" aria-hidden="true" />
          <h1 className="font-display text-titular font-extrabold tracking-tight text-marca">
            {titulo}
            {subtitulo && (
              <span className="ml-2 font-sans text-base font-normal text-tinta-2">
                {subtitulo}
              </span>
            )}
          </h1>

          <nav className="flex flex-wrap gap-2">
            {RUTAS.map((r) => (
              <NavLink key={r.a} to={r.a} end={r.a === "/"}
                       className={({ isActive }) =>
                         isActive
                           ? "rounded-full bg-marca px-4 py-1.5 font-semibold text-white"
                           : "rounded-full px-4 py-1.5 text-tinta hover:bg-marca-suave/50"}>
                {r.texto}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto">{acciones}</div>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1200px] grid-cols-12 gap-x-6 gap-y-8 px-6 py-8">
        {children}
      </main>
    </div>
  );
}
