import { Loader2 } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { ErrorBox } from "../components/ui";
import { useAuth } from "../lib/auth";
import { useTitle } from "../lib/useTitle";

function destinoSeguro(raw: string | null): string {
  // Solo rutas internas: evita redirecciones abiertas (?siguiente=https://...).
  return raw && raw.startsWith("/") && !raw.startsWith("//") ? raw : "/cuenta";
}

export default function Entrar() {
  const [params] = useSearchParams();
  const [modo, setModo] = useState<"entrar" | "registro">(params.get("modo") === "registro" ? "registro" : "entrar");
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string>();
  const [enviando, setEnviando] = useState(false);
  const { usuario, entrar, registrarse } = useAuth();
  const navigate = useNavigate();
  const siguiente = destinoSeguro(params.get("siguiente"));
  useTitle(modo === "entrar" ? "Iniciar sesión" : "Crear cuenta");

  if (usuario) return <Navigate to={siguiente} replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(undefined);
    setEnviando(true);
    try {
      if (modo === "entrar") await entrar(email, password);
      else await registrarse(nombre, email, password);
      navigate(siguiente, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo continuar.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <div className="card">
        <div role="tablist" aria-label="Acceso" className="mb-6 grid grid-cols-2 rounded-xl bg-ink-800 p-1">
          {(["entrar", "registro"] as const).map((m) => (
            <button
              key={m}
              role="tab"
              aria-selected={modo === m}
              onClick={() => {
                setModo(m);
                setError(undefined);
              }}
              className={`rounded-lg py-2 text-sm font-medium transition ${
                modo === m ? "bg-emerald-500 text-ink-950" : "text-slate-300 hover:text-white"
              }`}
            >
              {m === "entrar" ? "Iniciar sesión" : "Crear cuenta"}
            </button>
          ))}
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          {modo === "registro" && (
            <label className="block text-sm text-slate-300">
              Nombre
              <input
                className="input mt-1"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                autoComplete="name"
                required
                minLength={2}
                maxLength={80}
              />
            </label>
          )}
          <label className="block text-sm text-slate-300">
            Correo electrónico
            <input
              className="input mt-1"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </label>
          <label className="block text-sm text-slate-300">
            Contraseña
            <input
              className="input mt-1"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={modo === "entrar" ? "current-password" : "new-password"}
              required
              minLength={modo === "registro" ? 8 : 1}
              maxLength={128}
            />
            {modo === "registro" && <span className="mt-1 block text-xs text-slate-500">Mínimo 8 caracteres.</span>}
          </label>
          {error && <ErrorBox message={error} />}
          <button className="btn-primary w-full" disabled={enviando}>
            {enviando && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
            {modo === "entrar" ? "Entrar" : "Crear cuenta gratis"}
          </button>
        </form>
      </div>
      <p className="mt-4 text-center text-xs text-slate-500">
        Al crear una cuenta confirmas que eres mayor de 18 años.
      </p>
    </div>
  );
}
