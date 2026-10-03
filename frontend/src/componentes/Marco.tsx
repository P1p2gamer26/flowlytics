import { NavLink } from "react-router-dom";
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
      <header className="border-b border-tinta-2/15 bg-panel">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center gap-x-8 gap-y-3
                        px-6 py-4">
          <h1 className="font-display text-titular font-extrabold tracking-tight">
            {titulo}
            {subtitulo && (
              <span className="ml-2 font-sans text-base font-normal text-tinta-2">
                {subtitulo}
              </span>
            )}
          </h1>

          {/* La ruta activa se marca con el verde del sistema, el mismo que
              significa "en calma" en la cinta: aquí dice "estás aquí". */}
          <nav className="flex flex-wrap gap-5">
            {RUTAS.map((r) => (
              <NavLink key={r.a} to={r.a} end={r.a === "/"}
                       className={({ isActive }) =>
                         isActive
                           ? "border-b-2 border-calma pb-0.5 font-medium text-tinta"
                           : "border-b-2 border-transparent pb-0.5 text-tinta-2 hover:text-tinta"}>
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
