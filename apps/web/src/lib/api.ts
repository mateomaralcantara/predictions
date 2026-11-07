// Cliente tipado de la API. En desarrollo Vite redirige /backend -> :8000.
const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") || "/backend";

const TOKEN_KEY = "prd_token";

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string | null) {
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* almacenamiento no disponible (modo privado) */
    }
  },
};

/** Se emite cuando el servidor rechaza la sesión guardada. */
export const SESION_EXPIRADA = "prd:sesion-expirada";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

type Query = Record<string, string | number | undefined | null>;

export function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  }
  const qs = params.toString();
  return `${BASE}${path}${qs ? `?${qs}` : ""}`;
}

async function request<T>(path: string, init?: RequestInit & { query?: Query }): Promise<T> {
  const { query, ...rest } = init ?? {};
  const token = tokenStore.get();
  let res: Response;
  try {
    res = await fetch(buildUrl(path, query), {
      ...rest,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(rest.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor. ¿Está la API encendida?");
  }
  if (res.status === 401 && token) {
    tokenStore.set(null);
    window.dispatchEvent(new Event(SESION_EXPIRADA));
  }
  if (!res.ok) {
    let detail = res.status === 429 ? "Demasiadas solicitudes. Espera un momento." : `Error ${res.status}`;
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
  max_historial: number;
  limitado: boolean;
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
  solicitadas: number;
  max_jugadas: number;
  limitado: boolean;
  nivel: number;
}

export interface Plan {
  id: string;
  nombre: string;
  precio: string;
  moneda: string;
  descripcion: string;
  beneficios: string[];
  destacado: boolean;
  nivel: number;
  dias: number;
}

export interface Perfil {
  id: number;
  email: string;
  nombre: string;
  es_admin: boolean;
  creado_en: string;
  nivel: number;
  plan: { id: string; nombre: string; nivel: number; beneficios: string[] };
  suscripcion_vence: string | null;
  limites: { jugadas: number; historial: number; chat_por_minuto: number };
}

export interface Sesion {
  token: string;
  usuario: Perfil;
}

export interface Pago {
  id: string;
  plan: string;
  monto: string;
  moneda: string;
  estado: string;
  fecha: string;
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
  usuario?: Perfil;
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
  planes: () =>
    request<{ pagos_habilitados: boolean; gratis: { beneficios: string[] }; planes: Plan[] }>("/api/pagos/planes"),
  registro: (nombre: string, email: string, password: string) =>
    request<Sesion>("/api/auth/registro", { method: "POST", body: JSON.stringify({ nombre, email, password }) }),
  login: (email: string, password: string) =>
    request<Sesion>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  yo: () => request<Perfil>("/api/auth/yo"),
  misPagos: () => request<Pago[]>("/api/auth/pagos"),
  cambiarPassword: (actual: string, nueva: string) =>
    request<{ ok: boolean }>("/api/auth/password", { method: "POST", body: JSON.stringify({ actual, nueva }) }),
  crearOrden: (plan: string) =>
    request<Orden>("/api/pagos/ordenes", { method: "POST", body: JSON.stringify({ plan }) }),
  capturarOrden: (orderId: string) =>
    request<Captura>(`/api/pagos/ordenes/${encodeURIComponent(orderId)}/captura`, { method: "POST" }),
};
