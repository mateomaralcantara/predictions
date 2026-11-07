import { api } from "../lib/api";
import { useApi } from "../lib/useApi";

/** Selector de lotería. `value` es el nombre exacto o "" para todas. */
export function LoteriaSelector({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { data, error } = useApi(() => api.loterias(), []);
  const opciones = data ?? [];

  return (
    <label className="flex items-center gap-2 text-sm text-slate-300">
      <span className="hidden sm:inline">Lotería</span>
      <select
        className="input w-auto min-w-[14rem]"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={!!error}
        aria-label="Seleccionar lotería"
      >
        <option value="">Todas las loterías</option>
        {opciones.map((l) => (
          <option key={l.nombre} value={l.nombre}>
            {l.nombre} ({l.sorteos.toLocaleString("es-DO")})
          </option>
        ))}
      </select>
    </label>
  );
}
