import { Flame, Snowflake, Trophy } from "lucide-react";
import type { Resumen } from "../lib/api";
import { fecha, miles } from "../lib/format";
import { Ball, Balls } from "./ui";

export function ResumenTarjetas({ r }: { r: Resumen }) {
  if (!r.ultimo_sorteo) return <p className="text-sm text-slate-400">Sin sorteos para esta selección.</p>;
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <div className="card">
        <p className="card-title flex items-center gap-2">
          <Trophy className="h-4 w-4 text-emerald-400" aria-hidden /> Último sorteo
        </p>
        <div className="mt-3">
          <Balls nums={r.ultimo_sorteo.numeros} size="lg" />
        </div>
        <p className="mt-3 text-sm text-slate-400">
          {r.ultimo_sorteo.loteria} · {fecha(r.ultimo_sorteo.fecha)}
        </p>
      </div>
      <div className="card">
        <p className="card-title flex items-center gap-2">
          <Flame className="h-4 w-4 text-amber-400" aria-hidden /> Más frecuente ({r.dias_recientes} días)
        </p>
        {r.mas_frecuente_reciente ? (
          <>
            <div className="mt-3">
              <Ball n={r.mas_frecuente_reciente.numero} tone="amber" size="lg" />
            </div>
            <p className="mt-3 text-sm text-slate-400">{r.mas_frecuente_reciente.apariciones} apariciones</p>
          </>
        ) : (
          <p className="mt-3 text-sm text-slate-500">—</p>
        )}
      </div>
      <div className="card">
        <p className="card-title flex items-center gap-2">
          <Snowflake className="h-4 w-4 text-sky-400" aria-hidden /> Más atrasado
        </p>
        {r.mas_atrasado ? (
          <>
            <div className="mt-3">
              <Ball n={r.mas_atrasado.numero} tone="sky" size="lg" />
            </div>
            <p className="mt-3 text-sm text-slate-400">
              {miles(r.mas_atrasado.sorteos_sin_salir)} sorteos sin salir
              {r.mas_atrasado.ultima_fecha && ` · desde ${fecha(r.mas_atrasado.ultima_fecha)}`}
            </p>
          </>
        ) : (
          <p className="mt-3 text-sm text-slate-500">—</p>
        )}
      </div>
    </div>
  );
}

