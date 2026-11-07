import { AlertTriangle, Loader2, RotateCw } from "lucide-react";
import type { ReactNode } from "react";
import { dos } from "../lib/format";

type BallTone = "green" | "amber" | "sky" | "slate";

const tones: Record<BallTone, string> = {
  green: "from-emerald-300 to-emerald-600 text-emerald-950",
  amber: "from-amber-200 to-amber-500 text-amber-950",
  sky: "from-sky-200 to-sky-500 text-sky-950",
  slate: "from-slate-200 to-slate-400 text-slate-900",
};

export function Ball({ n, tone = "green", size = "md" }: { n: number; tone?: BallTone; size?: "sm" | "md" | "lg" }) {
  const sz = size === "lg" ? "h-14 w-14 text-xl" : size === "sm" ? "h-8 w-8 text-xs" : "h-10 w-10 text-sm";
  return (
    <span
      className={`inline-flex ${sz} shrink-0 items-center justify-center rounded-full bg-gradient-to-br font-mono font-bold shadow-inner shadow-white/40 ring-1 ring-black/20 ${tones[tone]}`}
    >
      {dos(n)}
    </span>
  );
}

export function Balls({ nums, tone, size }: { nums: number[]; tone?: BallTone; size?: "sm" | "md" | "lg" }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {nums.map((n, i) => (
        <Ball key={`${n}-${i}`} n={n} tone={tone} size={size} />
      ))}
    </div>
  );
}

export function Loading({ label = "Cargando…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 py-6 text-sm text-slate-400">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> {label}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
      <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden />
      <span className="flex-1">{message}</span>
      {onRetry && (
        <button className="btn-ghost py-1" onClick={onRetry}>
          <RotateCw className="h-3.5 w-3.5" aria-hidden /> Reintentar
        </button>
      )}
    </div>
  );
}

/** Renderiza loading / error / contenido de un estado de useApi. */
export function Async<T>({
  state,
  children,
  loadingLabel,
}: {
  state: { data: T | undefined; error: string | undefined; loading: boolean; reload: () => void };
  children: (data: T) => ReactNode;
  loadingLabel?: string;
}) {
  if (state.error) return <ErrorBox message={state.error} onRetry={state.reload} />;
  if (state.loading && state.data === undefined) return <Loading label={loadingLabel} />;
  if (state.data === undefined) return null;
  return <div className={state.loading ? "opacity-60 transition-opacity" : "transition-opacity"}>{children(state.data)}</div>;
}

export function PageHeader({ title, subtitle, children }: { title: string; subtitle?: string; children?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-slate-400">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

export function Disclaimer({ children }: { children: ReactNode }) {
  return (
    <p className="flex items-start gap-2 rounded-xl border border-amber-400/20 bg-amber-400/5 p-3 text-xs leading-relaxed text-amber-100/80">
      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-300" aria-hidden />
      <span>{children}</span>
    </p>
  );
}
