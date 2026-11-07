import { useCallback, useEffect, useRef, useState } from "react";

export interface ApiState<T> {
  data: T | undefined;
  error: string | undefined;
  loading: boolean;
  reload: () => void;
}

/** Ejecuta `fn` cuando cambian `deps`, ignorando respuestas obsoletas. */
export function useApi<T>(fn: () => Promise<T>, deps: unknown[]): ApiState<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    let vigente = true;
    setLoading(true);
    setError(undefined);
    fnRef
      .current()
      .then((d) => vigente && setData(d))
      .catch((e: unknown) => vigente && setError(e instanceof Error ? e.message : "Error inesperado"))
      .finally(() => vigente && setLoading(false));
    return () => {
      vigente = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload };
}
