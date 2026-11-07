import { ArrowLeft, CalendarDays, Flame, Grid3x3, Snowflake, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LoteriaSelector } from "../components/LoteriaSelector";
import { Mejorar } from "../components/Mejorar";
import { ResumenTarjetas } from "../components/ResumenTarjetas";
import { Async, Ball, Balls, Disclaimer } from "../components/ui";
import { api, type CeldaMapa, type DetalleLoteria } from "../lib/api";
import { useAuth } from "../lib/auth";
import { dos, fecha, miles } from "../lib/format";
import { useApi } from "../lib/useApi";
import { useTitle } from "../lib/useTitle";

const tooltipStyle = { background: "#11161d", border: "1px solid #ffffff1a", borderRadius: 12 };

function Seccion({ id, titulo, children, className = "" }: { id: string; titulo: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`card min-w-0 ${className}`} aria-labelledby={id}>
      <h2 id={id} className="card-title mb-4">
        {titulo}
      </h2>
      {children}
    </section>
  );
}

function Pronostico({ nombre }: { nombre: string }) {
  const [params, setParams] = useSearchParams();
  const jugadas = Math.min(10, Math.max(1, Number(params.get("jugadas")) || 5));
  const { usuario } = useAuth();
  const state = useApi(() => api.pronosticoLoteria(nombre, jugadas), [nombre, jugadas, usuario?.nivel]);

  return (
    <section className="card min-w-0 border-emerald-400/30" aria-labelledby="pronostico-title">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 id="pronostico-title" className="card-title flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-amber-300" aria-hidden /> Pronóstico para el próximo sorteo
        </h2>
        <select
          className="input w-auto py-1.5"
          value={jugadas}
          aria-label="Cantidad de jugadas"
          onChange={(e) =>
            setParams(
              (prev) => {
                const next = new URLSearchParams(prev);
                next.set("jugadas", e.target.value);
                return next;
              },
              { replace: true },
            )
          }
        >
          {[3, 5, 8, 10].map((n) => (
            <option key={n} value={n}>
              {n} jugadas
            </option>
          ))}
        </select>
      </div>
      <Async state={state} loadingLabel="Calculando pronóstico…">
        {(p) => (
          <div className="space-y-4">
            {p.limitado && (
              <Mejorar>
                Mostrando {p.jugadas.length} de {p.solicitadas} jugadas. Tu plan permite hasta {p.max_jugadas}.
              </Mejorar>
            )}
            <ol className="grid gap-3 sm:grid-cols-2">
              {p.jugadas.map((j, i) => (
                <li key={j.numeros.join("-")} className="rounded-xl bg-ink-800 p-3">
                  <div className="flex items-center gap-3">
                    <span className="w-5 font-mono text-xs text-slate-500">{String(i + 1).padStart(2, "0")}</span>
                    <Balls nums={j.numeros} />
                  </div>
                  <p className="mt-2 pl-8 text-xs text-slate-400">
                    Palés: {j.pales.map((pl) => pl.map(dos).join("-")).join(" · ")}
                  </p>
                </li>
              ))}
            </ol>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-amber-400/20 p-3">
                <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-amber-200">
                  <Flame className="h-3.5 w-3.5" aria-hidden /> Calientes (frecuencia reciente)
                </p>
                <Balls nums={p.calientes} tone="amber" size="sm" />
              </div>
              <div className="rounded-xl border border-sky-400/20 p-3">
                <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-sky-200">
                  <Snowflake className="h-3.5 w-3.5" aria-hidden /> Fríos (más atrasados)
                </p>
                <Balls nums={p.frios} tone="sky" size="sm" />
              </div>
            </div>
            <Disclaimer>
              {p.aviso} Calculado con {miles(p.basado_en.sorteos)} sorteos hasta el {fecha(p.basado_en.hasta)}.
            </Disclaimer>
          </div>
        )}
      </Async>
    </section>
  );
}

type ModoMapa = "apariciones" | "sorteos_sin_salir";

function MapaCalor({ mapa, nombre }: { mapa: CeldaMapa[]; nombre: string }) {
  const [modo, setModo] = useState<ModoMapa>("apariciones");
  const valores = mapa.map((c) => c[modo]);
  const min = Math.min(...valores);
  const max = Math.max(...valores);
  const color = modo === "apariciones" ? "16, 185, 129" : "56, 189, 248";

  return (
    <section className="card min-w-0" aria-labelledby="mapa-title">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 id="mapa-title" className="card-title flex items-center gap-2">
          <Grid3x3 className="h-4 w-4" aria-hidden /> Mapa de números 00–99
        </h2>
        <div role="tablist" aria-label="Métrica del mapa" className="flex rounded-xl border border-white/10 bg-ink-900 p-1 text-xs">
          {(
            [
              ["apariciones", "Frecuencia"],
              ["sorteos_sin_salir", "Atraso"],
            ] as const
          ).map(([k, label]) => (
            <button
              key={k}
              role="tab"
              aria-selected={modo === k}
              onClick={() => setModo(k)}
              className={`rounded-lg px-3 py-1 font-medium ${modo === k ? "bg-white/10 text-white" : "text-slate-400 hover:text-white"}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-10 gap-1">
        {mapa.map((c) => {
          const t = max > min ? (c[modo] - min) / (max - min) : 0;
          return (
            <Link
              key={c.numero}
              to={`/explorar?numero=${c.numero}&loteria=${encodeURIComponent(nombre)}`}
              title={`${dos(c.numero)} · ${c.apariciones} veces · ${c.sorteos_sin_salir} sorteos sin salir${
                c.ultima_fecha ? ` · última: ${c.ultima_fecha}` : ""
              }`}
              className="flex aspect-square items-center justify-center rounded-md font-mono text-[11px] font-semibold text-white ring-white/40 transition hover:ring-2 sm:text-xs"
              style={{ backgroundColor: `rgba(${color}, ${0.08 + t * 0.85})` }}
            >
              {dos(c.numero)}
            </Link>
          );
        })}
      </div>
      <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
        <span>{modo === "apariciones" ? "Menos frecuente" : "Salió hace poco"}</span>
        <span
          className="h-2 flex-1 mx-3 rounded-full"
          style={{ background: `linear-gradient(to right, rgba(${color},0.08), rgba(${color},0.93))` }}
        />
        <span>{modo === "apariciones" ? "Más frecuente" : "Más atrasado"}</span>
      </div>
    </section>
  );
}

function Contenido({ d }: { d: DetalleLoteria }) {
  return (
    <div className="space-y-6">
      <ResumenTarjetas r={d.resumen} />

      <div className="grid items-start gap-6 xl:grid-cols-5">
        <div className="xl:col-span-3">
          <Pronostico nombre={d.nombre} />
        </div>
        <div className="xl:col-span-2">
          <MapaCalor mapa={d.mapa} nombre={d.nombre} />
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <Seccion id="top-title" titulo="Top 10 números más salidos" className="lg:col-span-3">
          <div className="h-72 w-full">
            <ResponsiveContainer>
              <BarChart data={d.top.map((r) => ({ ...r, label: dos(r.numero) }))} margin={{ left: -16, right: 8 }}>
                <CartesianGrid stroke="#ffffff10" vertical={false} />
                <XAxis dataKey="label" stroke="#94a3b8" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} fontSize={12} allowDecimals={false} />
                <Tooltip
                  cursor={{ fill: "#ffffff08" }}
                  contentStyle={tooltipStyle}
                  labelFormatter={(l) => `Número ${l}`}
                  formatter={(v: number) => [miles(v), "Apariciones"]}
                />
                <Bar dataKey="apariciones" fill="#10b981" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Seccion>

        <Seccion id="pos-title" titulo="Más salidos por premio" className="lg:col-span-2">
          <div className="grid grid-cols-3 gap-3">
            {(["primer", "segundo", "tercero"] as const).map((pos, i) => (
              <div key={pos}>
                <p className="mb-2 text-center text-xs text-slate-400">{i + 1}.º premio</p>
                <ul className="space-y-2">
                  {d.posiciones[pos].map((f) => (
                    <li key={f.numero} className="flex items-center justify-between gap-1 rounded-lg bg-ink-800 px-2 py-1.5">
                      <Ball n={f.numero} size="sm" />
                      <span className="text-xs text-slate-400">{f.apariciones}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Seccion>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Seccion id="atr-title" titulo="Más atrasados">
          <ul className="divide-y divide-white/5">
            {d.atrasados.map((a) => (
              <li key={a.numero} className="flex items-center justify-between py-2">
                <Ball n={a.numero} tone="sky" size="sm" />
                <span className="text-right text-xs text-slate-400">
                  {miles(a.sorteos_sin_salir)} sorteos
                  {a.ultima_fecha && <span className="block text-slate-500">desde {fecha(a.ultima_fecha)}</span>}
                </span>
              </li>
            ))}
          </ul>
        </Seccion>
        <Seccion id="pales-title" titulo="Palés más repetidos">
          <ul className="divide-y divide-white/5">
            {d.pales.map((p) => (
              <li key={p.pale.join("-")} className="flex items-center justify-between py-2">
                <Balls nums={p.pale} size="sm" tone="amber" />
                <span className="text-xs text-slate-400">{p.apariciones} veces</span>
              </li>
            ))}
          </ul>
        </Seccion>
        <Seccion id="ternas-title" titulo="Ternas más repetidas">
          <ul className="divide-y divide-white/5">
            {d.combinaciones.map((c) => (
              <li key={c.combinacion.join("-")} className="flex items-center justify-between py-2">
                <Balls nums={c.combinacion} size="sm" tone="slate" />
                <span className="text-xs text-slate-400">{c.apariciones} veces</span>
              </li>
            ))}
          </ul>
        </Seccion>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Seccion id="ult-title" titulo="Últimos 20 resultados" className="lg:col-span-2">
          <div className="max-h-[32rem] overflow-y-auto">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-ink-900 text-xs uppercase text-slate-500">
                <tr>
                  <th className="py-2 pr-4 font-medium">Fecha</th>
                  <th className="py-2 font-medium">1.º · 2.º · 3.º</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {d.ultimos.map((s) => (
                  <tr key={s.fecha}>
                    <td className="py-2 pr-4 text-slate-300">{fecha(s.fecha)}</td>
                    <td className="py-2">
                      <Balls nums={s.numeros} size="sm" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Seccion>
        <Seccion id="dias-title" titulo="Sorteos por día de la semana">
          <ul className="space-y-2">
            {d.dias_semana.map((x) => {
              const max = Math.max(...d.dias_semana.map((y) => y.sorteos), 1);
              return (
                <li key={x.dia} className="flex items-center gap-3 text-sm">
                  <CalendarDays className="h-3.5 w-3.5 shrink-0 text-slate-500" aria-hidden />
                  <span className="w-20 text-slate-300">{x.dia}</span>
                  <span className="h-2 flex-1 overflow-hidden rounded-full bg-ink-800">
                    <span className="block h-full rounded-full bg-emerald-500/70" style={{ width: `${(x.sorteos / max) * 100}%` }} />
                  </span>
                  <span className="w-12 text-right text-xs text-slate-400">{miles(x.sorteos)}</span>
                </li>
              );
            })}
          </ul>
        </Seccion>
      </div>
    </div>
  );
}

export default function LoteriaDetalle() {
  const { nombre = "" } = useParams();
  const navigate = useNavigate();
  const state = useApi(() => api.detalleLoteria(nombre), [nombre]);
  useTitle(nombre);

  return (
    <>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link to="/" className="mb-2 inline-flex items-center gap-1 text-sm text-slate-400 hover:text-white">
            <ArrowLeft className="h-4 w-4" aria-hidden /> Todas las loterías
          </Link>
          <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">{state.data?.nombre ?? nombre}</h1>
          {state.data?.resumen.desde && (
            <p className="mt-1 text-sm text-slate-400">
              {miles(state.data.resumen.total_sorteos)} sorteos · {fecha(state.data.resumen.desde)} –{" "}
              {fecha(state.data.resumen.hasta)}
            </p>
          )}
        </div>
        <LoteriaSelector
          value={state.data?.nombre ?? nombre}
          onChange={(v) => navigate(v ? `/loteria/${encodeURIComponent(v)}` : "/")}
        />
      </div>
      <Async state={state} loadingLabel="Cargando lotería…">
        {(d) => <Contenido d={d} />}
      </Async>
    </>
  );
}
