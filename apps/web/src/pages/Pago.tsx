import { CheckCircle2, XCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ErrorBox, Loading } from "../components/ui";
import { api, type Captura } from "../lib/api";

export function PagoExito() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [captura, setCaptura] = useState<Captura>();
  const [error, setError] = useState<string>();
  const iniciado = useRef(false);

  useEffect(() => {
    // StrictMode monta dos veces en desarrollo: capturar una sola vez.
    if (!token || iniciado.current) return;
    iniciado.current = true;
    api
      .capturarOrden(token)
      .then(setCaptura)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "No se pudo confirmar el pago."));
  }, [token]);

  if (!token) return <ErrorBox message="Falta el identificador de la orden de PayPal." />;

  return (
    <div className="card mx-auto max-w-lg text-center">
      {error ? (
        <ErrorBox message={error} />
      ) : !captura ? (
        <Loading label="Confirmando tu pago con PayPal…" />
      ) : (
        <>
          <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-400" aria-hidden />
          <h1 className="mt-4 text-2xl font-bold text-white">¡Pago confirmado!</h1>
          <p className="mt-2 text-slate-300">
            {captura.plan ? `Plan ${captura.plan.nombre}` : "Tu plan"} · {captura.monto} {captura.moneda}
          </p>
          <p className="mt-1 text-xs text-slate-500">Orden {captura.id}</p>
          <Link to="/predicciones" className="btn-primary mt-6">
            Ver predicciones
          </Link>
        </>
      )}
    </div>
  );
}

export function PagoCancelado() {
  return (
    <div className="card mx-auto max-w-lg text-center">
      <XCircle className="mx-auto h-12 w-12 text-slate-400" aria-hidden />
      <h1 className="mt-4 text-2xl font-bold text-white">Pago cancelado</h1>
      <p className="mt-2 text-slate-400">No se realizó ningún cargo.</p>
      <Link to="/planes" className="btn-ghost mt-6">
        Volver a planes
      </Link>
    </div>
  );
}

export function NoEncontrado() {
  return (
    <div className="card mx-auto max-w-lg text-center">
      <h1 className="text-2xl font-bold text-white">Página no encontrada</h1>
      <Link to="/" className="btn-primary mt-6">
        Ir al inicio
      </Link>
    </div>
  );
}
