import { useEffect } from "react";

const BASE = "Predictions RD";

export function useTitle(titulo?: string) {
  useEffect(() => {
    document.title = titulo ? `${titulo} · ${BASE}` : `${BASE} · Estadísticas de loterías dominicanas`;
  }, [titulo]);
}
