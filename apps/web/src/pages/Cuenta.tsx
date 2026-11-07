import { Crown, LogOut } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { Async, ErrorBox, Loading, PageHeader } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useApi } from "../lib/useApi";
import { useTitle } from "../lib/useTitle";

const fechaHora = new Intl.DateTimeFormat("es-DO", { dateStyle: "medium" });

function CambiarPassword() {
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [estado, setEstado] = useState<{ ok?: boolean; error?: string }>({});

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setEstado({});
    try {
      await api.cambiarPassword(actual, nueva);
      setActual("");
      setNueva("");
      setEstado({ ok: true });
    } catch (err) {
      setEstado({ error: err instanceof Error ? err.message : "Error" });
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <input
        className="input"
        type="password"
        placeholder="Contraseña actual"
        autoComplete="current-password"
        value={actual}
        onChange={(e) => setActual(e.target.value)}
        required
      />
      <input
        className="input"
        type="password"
        placeholder="Nueva contraseña (mín. 8)"
        autoComplete="new-password"
        minLength={8}
        value={nueva}
        onChange={(e) => setNueva(e.target.value)}
        required
      />
      {estado.error && <ErrorBox message={estado.error} />}
      {estado.ok && <p className="text-sm text-emerald-300">Contraseña actualizada.</p>}
      <button className="btn-ghost">Cambiar contraseña</button>
    </form>
  );
}

export default function Cuenta() {
  const { usuario, cargando, salir } = useAuth();
  const pagos = useApi(() => (usuario ? api.misPagos() : Promise.resolve([])), [usuario?.id]);
  useTitle("Mi cuenta");

  if (cargando) return <Loading />;
  if (!usuario) return <Navigate to="/entrar?siguiente=/cuenta" replace />;

  const premium = usuario.nivel > 0;
  return (
    <>
      <PageHeader title={`Hola, ${usuario.nombre}`} subtitle={usuario.email}>
        <button className="btn-ghost" onClick={salir}>
          <LogOut className="h-4 w-4" aria-hidden /> Cerrar sesión
        </button>
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="card lg:col-span-2" aria-labelledby="plan-title">
          <h2 id="plan-title" className="card-title mb-4">
            Tu plan
          </h2>
          <div className="flex flex-wrap items-center gap-3">
            <span
              className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold ${
                premium ? "bg-amber-400/15 text-amber-200" : "bg-white/10 text-slate-200"
              }`}
            >
              {premium && <Crown className="h-4 w-4" aria-hidden />} {usuario.plan.nombre}
            </span>
            {usuario.suscripcion_vence && (
              <span className="text-sm text-slate-400">
                Activo hasta el {fechaHora.format(new Date(usuario.suscripcion_vence))}
              </span>
            )}
          </div>
          <dl className="mt-5 grid grid-cols-3 gap-2 text-center">
            {[
              ["Jugadas por juego", usuario.limites.jugadas],
              ["Historial por número", usuario.limites.historial],
              ["Preguntas/min", usuario.limites.chat_por_minuto],
            ].map(([k, v]) => (
              <div key={k} className="rounded-xl bg-ink-800 p-3">
                <dd className="text-xl font-bold text-white">{v}</dd>
                <dt className="text-xs text-slate-400">{k}</dt>
              </div>
            ))}
          </dl>
          <Link to="/planes" className="btn-primary mt-5">
            {premium ? "Ampliar o renovar" : "Ver planes"}
          </Link>
        </section>

        <section className="card" aria-labelledby="seguridad-title">
          <h2 id="seguridad-title" className="card-title mb-4">
            Seguridad
          </h2>
          <CambiarPassword />
        </section>

        <section className="card lg:col-span-3" aria-labelledby="pagos-title">
          <h2 id="pagos-title" className="card-title mb-4">
            Historial de pagos
          </h2>
          <Async state={pagos}>
            {(rows) =>
              rows.length ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="text-xs uppercase text-slate-500">
                      <tr>
                        <th className="py-2 pr-4">Fecha</th>
                        <th className="py-2 pr-4">Plan</th>
                        <th className="py-2 pr-4">Monto</th>
                        <th className="py-2 pr-4">Estado</th>
                        <th className="py-2">Orden</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-slate-300">
                      {rows.map((p) => (
                        <tr key={p.id}>
                          <td className="py-2 pr-4">{fechaHora.format(new Date(p.fecha))}</td>
                          <td className="py-2 pr-4">{p.plan}</td>
                          <td className="py-2 pr-4">
                            {p.monto} {p.moneda}
                          </td>
                          <td className="py-2 pr-4">{p.estado.toLowerCase()}</td>
                          <td className="py-2 font-mono text-xs text-slate-500">{p.id}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-slate-400">Aún no tienes pagos.</p>
              )
            }
          </Async>
        </section>
      </div>
    </>
  );
}
