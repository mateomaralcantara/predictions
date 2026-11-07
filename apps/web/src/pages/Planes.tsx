import { Check, Loader2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Async, Disclaimer, ErrorBox, PageHeader } from "../components/ui";
import { api, type Plan } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useApi } from "../lib/useApi";
import { useTitle } from "../lib/useTitle";

function Beneficios({ items }: { items: string[] }) {
  return (
    <ul className="mt-5 flex-1 space-y-2">
      {items.map((b) => (
        <li key={b} className="flex items-start gap-2 text-sm text-slate-300">
          <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" aria-hidden />
          {b}
        </li>
      ))}
    </ul>
  );
}

function TarjetaPlan({ plan, habilitado }: { plan: Plan; habilitado: boolean }) {
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string>();
  const { usuario } = useAuth();
  const navigate = useNavigate();
  const actual = usuario?.plan.id === plan.id;

  async function comprar() {
    if (!usuario) {
      navigate(`/entrar?modo=registro&siguiente=${encodeURIComponent("/planes")}`);
      return;
    }
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
      {(plan.destacado || actual) && (
        <span
          className={`absolute -top-3 left-5 rounded-full px-3 py-0.5 text-xs font-bold ${
            actual ? "bg-amber-400 text-amber-950" : "bg-emerald-500 text-ink-950"
          }`}
        >
          {actual ? "Tu plan" : "Más popular"}
        </span>
      )}
      <h2 className="text-lg font-semibold text-white">{plan.nombre}</h2>
      <p className="mt-1 text-sm text-slate-400">{plan.descripcion}</p>
      <p className="mt-5 flex items-baseline gap-1">
        <span className="text-4xl font-bold text-white">${plan.precio}</span>
        <span className="text-sm text-slate-400">
          {plan.moneda} · {plan.dias} días
        </span>
      </p>
      <Beneficios items={plan.beneficios} />
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
        {!habilitado ? "Próximamente" : !usuario ? "Crear cuenta y pagar" : actual ? "Renovar 30 días" : "Pagar con PayPal"}
      </button>
    </article>
  );
}

export default function Planes() {
  const state = useApi(() => api.planes(), []);
  const { usuario } = useAuth();
  useTitle("Planes");
  return (
    <>
      <PageHeader
        title="Planes"
        subtitle="Pago único con PayPal por 30 días, sin renovación automática. Si renuevas el mismo plan, los días se suman."
      />
      <Async state={state}>
        {({ planes, pagos_habilitados, gratis }) => (
          <>
            {!pagos_habilitados && (
              <p className="mb-6 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-slate-300">
                Los pagos aún no están activos en este entorno.
              </p>
            )}
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
              <article className="card relative flex flex-col">
                {usuario && usuario.nivel === 0 && (
                  <span className="absolute -top-3 left-5 rounded-full bg-amber-400 px-3 py-0.5 text-xs font-bold text-amber-950">
                    Tu plan
                  </span>
                )}
                <h2 className="text-lg font-semibold text-white">Gratis</h2>
                <p className="mt-1 text-sm text-slate-400">Para conocer la herramienta.</p>
                <p className="mt-5 text-4xl font-bold text-white">$0</p>
                <Beneficios items={gratis.beneficios} />
              </article>
              {planes.map((p) => (
                <TarjetaPlan key={p.id} plan={p} habilitado={pagos_habilitados} />
              ))}
            </div>
            <div className="mt-6">
              <Disclaimer>
                Los planes dan acceso a más análisis, no a mejores probabilidades: ningún sistema puede predecir un
                sorteo aleatorio.
              </Disclaimer>
            </div>
          </>
        )}
      </Async>
    </>
  );
}
