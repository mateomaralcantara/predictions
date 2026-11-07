import { Sparkles } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { Mejorar } from "../components/Mejorar";
import { Async, Balls, Disclaimer, PageHeader } from "../components/ui";
import { api, type Prediccion } from "../lib/api";
import { fecha, miles } from "../lib/format";
import { useAuth } from "../lib/auth";
import { useApi } from "../lib/useApi";
import { useTitle } from "../lib/useTitle";

const JUEGOS = [
  { id: "loto", label: "Loto LEIDSA" },
  { id: "superkino", label: "SuperKino" },
] as const;

type JuegoId = (typeof JUEGOS)[number]["id"];

function Resultado({ p }: { p: Prediccion }) {
  const u = p.ultimo_sorteo;
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <aside className="card h-fit">
        <h2 className="card-title mb-3">Último sorteo</h2>
        <Balls nums={u.numeros} size="sm" tone="slate" />
        {u.mas !== undefined && (
          <p className="mt-3 text-sm text-slate-300">
            Más <strong className="font-mono">{u.mas}</strong> · Súper Más{" "}
            <strong className="font-mono">{u.super_mas}</strong>
          </p>
        )}
        <p className="mt-2 text-sm text-slate-400">{fecha(u.fecha)}</p>
        <hr className="my-4 border-white/5" />
        <p className="text-xs leading-relaxed text-slate-400">
          {p.reglas}. Modelo calculado sobre {miles(p.historico.sorteos)} sorteos ({fecha(p.historico.desde)} –{" "}
          {fecha(p.historico.hasta)}). Las jugadas solo cambian cuando entra un sorteo nuevo.
        </p>
      </aside>

      <section className="lg:col-span-2" aria-label="Jugadas sugeridas">
        {p.limitado && (
          <div className="mb-3">
            <Mejorar>
              Mostrando {p.jugadas.length} de {p.solicitadas} jugadas. Tu plan permite hasta {p.max_jugadas} por juego.
            </Mejorar>
          </div>
        )}
        <ol className="space-y-3">
          {p.jugadas.map((j, i) => (
            <li key={j.numeros.join("-")} className="card flex flex-wrap items-center gap-4 p-4">
              <span className="w-6 font-mono text-sm text-slate-500">{String(i + 1).padStart(2, "0")}</span>
              <div className="flex-1">
                <Balls nums={j.numeros} />
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                {j.mas !== undefined && (
                  <span className="chip border-amber-400/30 text-amber-200">Más {j.mas}</span>
                )}
                {j.super_mas !== undefined && (
                  <span className="chip border-sky-400/30 text-sky-200">Súper Más {j.super_mas}</span>
                )}
                <span>
                  {j.pares}P / {j.impares}I
                </span>
              </div>
            </li>
          ))}
        </ol>
        <div className="mt-4">
          <Disclaimer>{p.aviso}</Disclaimer>
        </div>
      </section>
    </div>
  );
}

export default function Predicciones() {
  const [params, setParams] = useSearchParams();
  const juego: JuegoId = params.get("juego") === "superkino" ? "superkino" : "loto";
  const jugadas = Math.min(10, Math.max(1, Number(params.get("jugadas")) || 5));
  const { usuario } = useAuth();
  const state = useApi(() => api.prediccion(juego, jugadas), [juego, jugadas, usuario?.nivel]);
  useTitle("Jugadas sugeridas");

  const set = (k: string, v: string) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set(k, v);
        return next;
      },
      { replace: true },
    );

  return (
    <>
      <PageHeader
        title="Jugadas sugeridas"
        subtitle="Combinaciones generadas con criterios heurísticos (recencia, pares frecuentes, equilibrio par/impar y por rangos)."
      >
        <div className="flex flex-wrap items-center gap-2">
          <div role="tablist" aria-label="Juego" className="flex rounded-xl border border-white/10 bg-ink-900 p-1">
            {JUEGOS.map((j) => (
              <button
                key={j.id}
                role="tab"
                aria-selected={juego === j.id}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                  juego === j.id ? "bg-emerald-500 text-ink-950" : "text-slate-300 hover:text-white"
                }`}
                onClick={() => set("juego", j.id)}
              >
                {j.label}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-300">
            <Sparkles className="h-4 w-4 text-amber-300" aria-hidden />
            <select
              className="input w-auto"
              value={jugadas}
              onChange={(e) => set("jugadas", e.target.value)}
              aria-label="Cantidad de jugadas"
            >
              {[3, 5, 8, 10].map((n) => (
                <option key={n} value={n}>
                  {n} jugadas
                </option>
              ))}
            </select>
          </label>
        </div>
      </PageHeader>

      <Async state={state} loadingLabel="Calculando jugadas…">
        {(p) => <Resultado p={p} />}
      </Async>
    </>
  );
}
