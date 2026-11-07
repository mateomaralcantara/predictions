import { Search } from "lucide-react";
import { type FormEvent, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { LoteriaSelector } from "../components/LoteriaSelector";
import { Mejorar } from "../components/Mejorar";
import { Async, Ball, Balls, PageHeader } from "../components/ui";
import { api } from "../lib/api";
import { dos, fecha, miles } from "../lib/format";
import { useAuth } from "../lib/auth";
import { useApi } from "../lib/useApi";
import { useTitle } from "../lib/useTitle";
import { useLoteria } from "../lib/useLoteria";

function BuscadorNumero({ loteria }: { loteria: string }) {
  const [params, setParams] = useSearchParams();
  const inicial = params.get("numero") ?? "";
  const [entrada, setEntrada] = useState(inicial);
  const numero = inicial === "" ? null : Number(inicial);
  const valido = numero !== null && Number.isInteger(numero) && numero >= 0 && numero <= 99;

  const { usuario } = useAuth();
  const info = useApi(
    () => (valido ? api.numero(numero, loteria || undefined, 500) : Promise.resolve(undefined)),
    [numero, loteria, valido, usuario?.nivel],
  );

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (entrada.trim()) next.set("numero", String(Number(entrada)));
        else next.delete("numero");
        return next;
      },
      { replace: true },
    );
  }

  const entradaNum = Number(entrada);
  const entradaValida = entrada.trim() !== "" && Number.isInteger(entradaNum) && entradaNum >= 0 && entradaNum <= 99;

  return (
    <section className="card" aria-labelledby="buscar-title">
      <h2 id="buscar-title" className="card-title mb-4">
        Historial de un número
      </h2>
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          className="input max-w-[8rem] font-mono"
          inputMode="numeric"
          type="number"
          min={0}
          max={99}
          value={entrada}
          onChange={(e) => setEntrada(e.target.value)}
          placeholder="00–99"
          aria-label="Número del 0 al 99"
        />
        <button className="btn-primary" disabled={!entradaValida}>
          <Search className="h-4 w-4" aria-hidden /> Buscar
        </button>
      </form>

      {numero !== null && !valido && <p className="mt-3 text-sm text-rose-300">Introduce un número entre 0 y 99.</p>}

      {valido && (
        <div className="mt-5">
          <Async state={info}>
            {(d) =>
              d && (
                <div>
                  <div className="flex flex-wrap items-center gap-4">
                    <Ball n={d.numero} size="lg" />
                    <div>
                      <p className="text-2xl font-bold text-white">{miles(d.total)} veces</p>
                      <p className="text-sm text-slate-400">Última vez: {fecha(d.ultima_fecha)}</p>
                    </div>
                  </div>
                  <dl className="mt-4 grid grid-cols-3 gap-2 text-center">
                    {(["primer", "segundo", "tercero"] as const).map((k, i) => (
                      <div key={k} className="rounded-xl bg-ink-800 p-3">
                        <dt className="text-xs text-slate-400">{i + 1}.º premio</dt>
                        <dd className="text-lg font-semibold text-white">{miles(d.posiciones[k])}</dd>
                      </div>
                    ))}
                  </dl>
                  {d.limitado && (
                    <div className="mt-4">
                      <Mejorar>
                        Ves las últimas {d.max_historial} de {d.total.toLocaleString("es-DO")} apariciones.
                      </Mejorar>
                    </div>
                  )}
                  {d.sorteos.length > 0 && (
                    <ul className="mt-4 max-h-72 divide-y divide-white/5 overflow-y-auto">
                      {d.sorteos.map((s) => (
                        <li key={`${s.fecha}-${s.loteria}`} className="flex items-center justify-between gap-3 py-2">
                          <span className="min-w-0 truncate text-sm text-slate-300">
                            {fecha(s.fecha)} · {s.loteria}
                          </span>
                          <Balls nums={s.numeros} size="sm" tone="slate" />
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )
            }
          </Async>
        </div>
      )}
    </section>
  );
}

export default function Explorar() {
  const [loteria, setLoteria] = useLoteria();
  const atrasados = useApi(() => api.atrasados(loteria || undefined, 10), [loteria]);
  const combinaciones = useApi(() => api.combinaciones(loteria || undefined, 8), [loteria]);
  useTitle("Explorar el histórico");

  return (
    <>
      <PageHeader title="Explorar el histórico" subtitle="Busca cualquier número y revisa atrasos y ternas repetidas.">
        <LoteriaSelector value={loteria} onChange={setLoteria} />
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-2">
        <BuscadorNumero loteria={loteria} />

        <div className="flex flex-col gap-6">
          <section className="card" aria-labelledby="atrasados-title">
            <h2 id="atrasados-title" className="card-title mb-4">
              Números más atrasados
            </h2>
            <Async state={atrasados}>
              {(rows) => (
                <ol className="grid grid-cols-2 gap-2 sm:grid-cols-5">
                  {rows.map((a) => (
                    <li key={a.numero} className="flex flex-col items-center rounded-xl bg-ink-800 p-3 text-center">
                      <Ball n={a.numero} tone="sky" />
                      <span className="mt-2 text-xs text-slate-400">{miles(a.sorteos_sin_salir)} sorteos</span>
                    </li>
                  ))}
                </ol>
              )}
            </Async>
          </section>

          <section className="card" aria-labelledby="ternas-title">
            <h2 id="ternas-title" className="card-title mb-4">
              Ternas más repetidas
            </h2>
            <Async state={combinaciones}>
              {(rows) => (
                <ul className="divide-y divide-white/5">
                  {rows.map((c) => (
                    <li key={c.combinacion.map(dos).join("-")} className="flex items-center justify-between py-2">
                      <Balls nums={c.combinacion} size="sm" tone="amber" />
                      <span className="text-sm text-slate-400">{c.apariciones} veces</span>
                    </li>
                  ))}
                </ul>
              )}
            </Async>
          </section>
        </div>
      </div>
    </>
  );
}
