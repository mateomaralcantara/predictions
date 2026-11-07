import { Check, Loader2 } from "lucide-react";
import { useState } from "react";
import { Async, ErrorBox, PageHeader } from "../components/ui";
import { api, type Plan } from "../lib/api";
import { useApi } from "../lib/useApi";

function TarjetaPlan({ plan, habilitado }: { plan: Plan; habilitado: boolean }) {
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string>();

  async function comprar() {
    setCargando(true);
    setError(undefined);
    try {
      const orden = await api.crearOrden(plan.id);
      window.location.assign(orden.approve_url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo iniciar el pago.");
      setCargando(false);
    }
  }

  return (
    <article
      className={`card relative flex flex-col ${plan.destacado ? "border-emerald-400/50 ring-1 ring-emerald-400/30" : ""}`}
    >
      {plan.destacado && (
        <span className="absolute -top-3 left-5 rounded-full bg-emerald-500 px-3 py-0.5 text-xs font-bold text-ink-950">
          Más popular
        </span>
      )}
      <h2 className="text-lg font-semibold text-white">{plan.nombre}</h2>
      <p className="mt-1 text-sm text-slate-400">{plan.descripcion}</p>
      <p className="mt-5 flex items-baseline gap-1">
        <span className="text-4xl font-bold text-white">${plan.precio}</span>
        <span className="text-sm text-slate-400">{plan.moneda}/mes</span>
      </p>
      <ul className="mt-5 flex-1 space-y-2">
        {plan.beneficios.map((b) => (
          <li key={b} className="flex items-start gap-2 text-sm text-slate-300">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" aria-hidden />
            {b}
          </li>
        ))}
      </ul>
      {error && (
        <div className="mt-4">
          <ErrorBox message={error} />
        </div>
      )}
      <button
        className={`mt-6 w-full ${plan.destacado ? "btn-primary" : "btn-ghost"}`}
        onClick={comprar}
        disabled={!habilitado || cargando}
      >
        {cargando && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
        {habilitado ? "Pagar con PayPal" : "Próximamente"}
      </button>
    </article>
  );
}

export default function Planes() {
  const state = useApi(() => api.planes(), []);
  return (
    <>
      <PageHeader title="Planes" subtitle="Elige el plan que mejor se ajuste a cómo juegas. Pago seguro con PayPal." />
      <Async state={state}>
        {({ planes, pagos_habilitados }) => (
          <>
            {!pagos_habilitados && (
              <p className="mb-6 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-slate-300">
                Los pagos aún no están activos en este entorno.
              </p>
            )}
            <div className="grid gap-6 md:grid-cols-3">
              {planes.map((p) => (
                <TarjetaPlan key={p.id} plan={p} habilitado={pagos_habilitados} />
              ))}
            </div>
          </>
        )}
      </Async>
    </>
  );
}
