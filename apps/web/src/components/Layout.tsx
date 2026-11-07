import { Menu, UserRound, X } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";

const LINKS = [
  { to: "/", label: "Inicio" },
  { to: "/explorar", label: "Explorar" },
  { to: "/predicciones", label: "Predicciones" },
  { to: "/planes", label: "Planes" },
];

function linkClass({ isActive }: { isActive: boolean }) {
  return `rounded-lg px-3 py-2 text-sm font-medium transition ${
    isActive ? "bg-white/10 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"
  }`;
}

export default function Layout() {
  const [abierto, setAbierto] = useState(false);
  const { pathname } = useLocation();
  const { usuario, cargando } = useAuth();
  const cuenta = usuario
    ? { to: "/cuenta", label: usuario.nombre.split(" ")[0] }
    : { to: `/entrar?siguiente=${encodeURIComponent(pathname)}`, label: "Entrar" };

  useEffect(() => {
    setAbierto(false);
    window.scrollTo({ top: 0 });
  }, [pathname]);

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#contenido" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 btn-primary">
        Saltar al contenido
      </a>
      <header className="sticky top-0 z-40 border-b border-white/5 bg-ink-950/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <NavLink to="/" className="flex items-center gap-2 font-bold tracking-tight text-white">
            <img src="/favicon.svg" alt="" className="h-7 w-7" />
            Predictions <span className="text-emerald-400">RD</span>
          </NavLink>
          <nav className="hidden items-center gap-1 sm:flex" aria-label="Principal">
            {LINKS.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.to === "/"} className={linkClass}>
                {l.label}
              </NavLink>
            ))}
            {!cargando && (
              <NavLink
                to={cuenta.to}
                className="ml-2 inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-white/5"
              >
                <UserRound className="h-4 w-4" aria-hidden />
                {cuenta.label}
                {usuario && usuario.nivel > 0 && (
                  <span className="rounded bg-amber-400/20 px-1.5 text-[10px] font-bold uppercase text-amber-200">
                    {usuario.plan.nombre}
                  </span>
                )}
              </NavLink>
            )}
          </nav>
          <button
            className="btn-ghost p-2 sm:hidden"
            onClick={() => setAbierto((v) => !v)}
            aria-expanded={abierto}
            aria-label={abierto ? "Cerrar menú" : "Abrir menú"}
          >
            {abierto ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
        {abierto && (
          <nav className="flex flex-col gap-1 border-t border-white/5 px-4 py-3 sm:hidden" aria-label="Móvil">
            {LINKS.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.to === "/"} className={linkClass}>
                {l.label}
              </NavLink>
            ))}
            <NavLink to={cuenta.to} className={linkClass}>
              {usuario ? "Mi cuenta" : "Entrar"}
            </NavLink>
          </nav>
        )}
      </header>

      <main id="contenido" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>

      <footer className="border-t border-white/5 py-6 text-center text-xs leading-relaxed text-slate-500">
        <p className="mx-auto max-w-3xl px-4">
          Herramienta informativa y de entretenimiento. Los sorteos son aleatorios: ninguna estadística ni predicción
          aumenta la probabilidad de ganar. Juega con responsabilidad · Solo mayores de 18 años.
        </p>
      </footer>
    </div>
  );
}
