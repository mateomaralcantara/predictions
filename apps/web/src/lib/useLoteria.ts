import { useSearchParams } from "react-router-dom";

/** Lotería seleccionada guardada en la URL (?loteria=...) para poder compartirla. */
export function useLoteria(): [string, (v: string) => void] {
  const [params, setParams] = useSearchParams();
  const loteria = params.get("loteria") ?? "";
  const set = (v: string) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (v) next.set("loteria", v);
        else next.delete("loteria");
        return next;
      },
      { replace: true },
    );
  return [loteria, set];
}
