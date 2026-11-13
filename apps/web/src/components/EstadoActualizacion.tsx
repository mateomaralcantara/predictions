import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Health } from "../lib/api";

const hora = new Intl.DateTimeFormat("es-DO", { hour: "numeric", minute: "2-digit" });

/** Indica si la API mantiene los sorteos al día y cuándo revisó por última vez. */
export function EstadoActualizacion() {
  const [h, setH] = useState<Health>();

  useEffect(() => {
    let vivo = true;
    const cargar = () =>
      api
        .health()
        .then((d) => vivo && setH(d))
        .catch(() => undefined);
    void cargar();
    const id = window.setInterval(cargar, 60_000);
    return () => {
      vivo = false;
      window.clearInterval(id);
    };
  }, []);

  const a = h?.actualizacion;
  if (!a?.activa) return null;
  return (
    <p className="mb-4 flex items-center gap-2 text-xs text-slate-400">
      <RefreshCw className={`h-3.5 w-3.5 text-emerald-400 ${a.en_curso ? "animate-spin" : ""}`} aria-hidden />
      {a.en_curso
        ? "Buscando sorteos nuevos…"
        : a.ultima
          ? `Se actualiza sola cada ${a.cada_min} min · última revisión ${hora.format(new Date(a.ultima))}`
          : `Se actualiza sola cada ${a.cada_min} min · primera revisión en curso`}
    </p>
  );
}
