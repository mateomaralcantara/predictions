import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { fecha, miles } from "../lib/format";
import { rutaLoteria } from "../lib/rutas";
import { useApi } from "../lib/useApi";
import { Async } from "./ui";

/** Tarjetas de todas las loterías; cada una abre su pantalla de detalle. */
export function LoteriasGrid() {
  const state = useApi(() => api.loterias(), []);
  return (
    <section aria-labelledby="loterias-title" className="mb-8">
      <h2 id="loterias-title" className="card-title mb-3">
        Elige una lotería
      </h2>
      <Async state={state}>
        {(rows) => (
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
            {rows.map((l) => (
              <li key={l.nombre}>
                <Link
                  to={rutaLoteria(l.nombre)}
                  className="group flex h-full flex-col justify-between rounded-2xl border border-white/10 bg-ink-900/80 p-4 transition hover:border-emerald-400/50 hover:bg-ink-800"
                >
                  <span className="flex items-start justify-between gap-2 text-sm font-semibold text-white">
                    {l.nombre}
                    <ChevronRight className="h-4 w-4 shrink-0 text-slate-500 transition group-hover:translate-x-0.5 group-hover:text-emerald-400" aria-hidden />
                  </span>
                  <span className="mt-3 text-xs text-slate-400">
                    {miles(l.sorteos)} sorteos · hasta {fecha(l.hasta)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Async>
    </section>
  );
}
