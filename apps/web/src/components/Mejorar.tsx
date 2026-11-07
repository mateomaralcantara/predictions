import { Lock } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth";

/** Aviso cuando el plan actual limita lo que se muestra. */
export function Mejorar({ children }: { children: React.ReactNode }) {
  const { usuario } = useAuth();
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-emerald-400/30 bg-emerald-400/5 p-3 text-sm text-emerald-100">
      <Lock className="h-4 w-4 shrink-0 text-emerald-300" aria-hidden />
      <span className="flex-1">{children}</span>
      <Link to={usuario ? "/planes" : "/entrar?siguiente=/planes"} className="btn-primary py-1.5">
        {usuario ? "Mejorar plan" : "Crear cuenta"}
      </Link>
    </div>
  );
}
