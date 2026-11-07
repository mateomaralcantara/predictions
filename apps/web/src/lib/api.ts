// Cliente tipado de la API. En desarrollo Vite redirige /backend -> :8000.
const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") || "/backend";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

type Query = Record<string, string | number | undefined | null>;

function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  }
  const qs = params.toString();
  return `${BASE}${path}${qs ? `?${qs}` : ""}`;
}

async function request<T>(path: string, init?: RequestInit & { query?: Query }): Promise<T> {
  const { query, ...rest } = init ?? {};
  let res: Response;
  try {
    res = await fetch(buildUrl(path, query), {
      ...rest,
      headers: { "Content-Type": "application/json", ...(rest.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor. ¿Está la API encendida?");
  }
  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

// ---- Tipos ---------------------------------------------------------------

export interface Health {
  estado: string;
  version: string;
  fuente_datos: string;
  sorteos: number;
  ultimo_sorteo: string | null;
  openai: boolean;
  pagos: boolean;
}

export interface Loteria {
  nombre: string;
  sorteos: number;
  desde: string;
  hasta: string;
}

export interface Sorteo {
  fecha: string;
  loteria: string;
  numeros: number[];
}

export interface Frecuencia {
  numero: number;
  apariciones: number;
}

export interface Atrasado {
  numero: number;
  sorteos_sin_salir: number;
  ultima_fecha: string | null;
}

export interface Combinacion {
  combinacion: number[];
  apariciones: number;
}

export interface Resumen {
  total_sorteos: number;
  desde?: string;
  hasta?: string;
  ultimo_sorteo: Sorteo | null;
  dias_recientes?: number;
  mas_frecuente_reciente: Frecuencia | null;
  mas_atrasado: Atrasado | null;
}

export interface InfoNumero {
  numero: number;
  total: number;
  ultima_fecha: string | null;
  posiciones: { primer: number; segundo: number; tercero: number };
  sorteos: Sorteo[];
}

export interface Jugada {
  numeros: number[];
  mas?: number;
  super_mas?: number;
  pares: number;
  impares: number;
}

export interface Prediccion {
  juego: "loto" | "superkino";
  nombre: string;
  reglas: string;
  historico: { sorteos: number; desde: string; hasta: string };
  ultimo_sorteo: { fecha: string; numeros: number[]; mas?: number; super_mas?: number };
  jugadas: Jugada[];
  aviso: string;
}

export interface Plan {
  id: string;
  nombre: string;
  precio: string;
  moneda: string;
  descripcion: string;
  beneficios: string[];
  destacado: boolean;
}

export interface Orden {
  id: string;
  estado: string;
  approve_url: string;
}

export interface Captura {
  id: string;
  estado: string;
  plan: Plan | null;
  monto: string | null;
  moneda: string | null;
}

// ---- Endpoints -------------------------------------------------------------

export const api = {
  health: () => request<Health>("/api/health"),
  loterias: () => request<Loteria[]>("/api/loterias"),
  resumen: (loteria?: string) => request<Resumen>("/api/estadisticas/resumen", { query: { loteria } }),
  top: (loteria?: string, limite = 10, year?: number) =>
    request<Frecuencia[]>("/api/estadisticas/top", { query: { loteria, limite, year } }),
  ultimos: (loteria?: string, limite = 8) =>
    request<Sorteo[]>("/api/estadisticas/ultimos", { query: { loteria, limite } }),
  atrasados: (loteria?: string, limite = 10) =>
    request<Atrasado[]>("/api/estadisticas/atrasados", { query: { loteria, limite } }),
  combinaciones: (loteria?: string, limite = 10) =>
    request<Combinacion[]>("/api/estadisticas/combinaciones", { query: { loteria, limite } }),
  numero: (numero: number, loteria?: string, limite = 20) =>
    request<InfoNumero>(`/api/estadisticas/numero/${numero}`, { query: { loteria, limite } }),
  prediccion: (juego: "loto" | "superkino", jugadas = 5) =>
    request<Prediccion>(`/api/predicciones/${juego}`, { query: { jugadas } }),
  chat: (pregunta: string) =>
    request<{ pregunta: string; intencion: string; respuesta: string }>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ pregunta }),
    }),
  planes: () => request<{ pagos_habilitados: boolean; planes: Plan[] }>("/api/pagos/planes"),
  crearOrden: (plan: string) =>
    request<Orden>("/api/pagos/ordenes", { method: "POST", body: JSON.stringify({ plan }) }),
  capturarOrden: (orderId: string) =>
    request<Captura>(`/api/pagos/ordenes/${encodeURIComponent(orderId)}/captura`, { method: "POST" }),
};
