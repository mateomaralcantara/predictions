import { CalendarClock, Flame, Snowflake, Trophy } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Chat from "../components/Chat";
import { LoteriaSelector } from "../components/LoteriaSelector";
import { Async, Ball, Balls, Disclaimer, PageHeader } from "../components/ui";
import { api, type Resumen } from "../lib/api";
import { dos, fecha, miles } from "../lib/format";
import { useApi } from "../lib/useApi";
import { useLoteria } from "../lib/useLoteria";

function diasDesde(iso?: string) {
  if (!iso) return 0;
  return Math.floor((Date.now() - new Date(`${iso}T00:00:00Z`).getTime()) / 86_400_000);
}

function Tarjetas({ r }: { r: Resumen }) {
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

export default function Inicio() {
  const [loteria, setLoteria] = useLoteria();
  const resumen = useApi(() => api.resumen(loteria || undefined), [loteria]);
  const top = useApi(() => api.top(loteria || undefined, 10), [loteria]);
  const ultimos = useApi(() => api.ultimos(loteria || undefined, 8), [loteria]);
  const atraso = diasDesde(resumen.data?.hasta);

  return (
    <>
      <PageHeader
        title="Resultados y estadísticas"
        subtitle="Histórico de las loterías dominicanas: qué salió, qué se repite y qué lleva tiempo sin salir."
      >
        <LoteriaSelector value={loteria} onChange={setLoteria} />
      </PageHeader>

      {resumen.data && atraso > 7 && (
        <div className="mb-4 flex items-center gap-2 rounded-xl border border-sky-400/20 bg-sky-400/5 p-3 text-sm text-sky-100/80">
          <CalendarClock className="h-4 w-4 shrink-0 text-sky-300" aria-hidden />
          Datos actualizados hasta el {fecha(resumen.data.hasta)} ({miles(resumen.data.total_sorteos)} sorteos desde{" "}
          {fecha(resumen.data.desde)}).
        </div>
      )}

      <Async state={resumen} loadingLabel="Cargando resumen…">
        {(r) => <Tarjetas r={r} />}
      </Async>

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <section className="card flex min-w-0 flex-col lg:col-span-3" aria-labelledby="top-title">
          <h2 id="top-title" className="card-title mb-4">
            Top 10 números más salidos
          </h2>
          <Async state={top}>
            {(rows) =>
              rows.length ? (
                <div className="h-72 w-full lg:h-[26rem]">
                  <ResponsiveContainer>
                    <BarChart data={rows.map((r) => ({ ...r, label: dos(r.numero) }))} margin={{ left: -16, right: 8 }}>
                      <CartesianGrid stroke="#ffffff10" vertical={false} />
                      <XAxis dataKey="label" stroke="#94a3b8" tickLine={false} axisLine={false} fontSize={12} />
                      <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} fontSize={12} allowDecimals={false} />
                      <Tooltip
                        cursor={{ fill: "#ffffff08" }}
                        contentStyle={{ background: "#11161d", border: "1px solid #ffffff1a", borderRadius: 12 }}
                        labelFormatter={(l) => `Número ${l}`}
                        formatter={(v: number) => [miles(v), "Apariciones"]}
                      />
                      <Bar dataKey="apariciones" fill="#10b981" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-sm text-slate-400">Sin datos.</p>
              )
            }
          </Async>
        </section>

        <section className="card min-w-0 lg:col-span-2" aria-labelledby="ultimos-title">
          <h2 id="ultimos-title" className="card-title mb-4">
            Últimos resultados
          </h2>
          <Async state={ultimos}>
            {(rows) => (
              <ul className="divide-y divide-white/5">
                {rows.map((s) => (
                  <li key={`${s.fecha}-${s.loteria}`} className="flex items-center justify-between gap-3 py-2.5">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-200">{s.loteria}</p>
                      <p className="text-xs text-slate-500">{fecha(s.fecha)}</p>
                    </div>
                    <Balls nums={s.numeros} size="sm" />
                  </li>
                ))}
              </ul>
            )}
          </Async>
        </section>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <div className="min-w-0 lg:col-span-3">
          <Chat />
        </div>
        <div className="flex min-w-0 flex-col gap-4 lg:col-span-2">
          <Disclaimer>
            Las frecuencias describen el pasado. En un sorteo justo cada número tiene la misma probabilidad en cada
            extracción, salga mucho o poco.
          </Disclaimer>
        </div>
      </div>
    </>
  );
}
