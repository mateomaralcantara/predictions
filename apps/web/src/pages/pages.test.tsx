import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { mockFetch, renderRuta } from "../test/helpers";
import { tokenStore } from "../lib/api";
import Entrar from "./Entrar";
import Planes from "./Planes";
import Predicciones from "./Predicciones";

const PERFIL = {
  id: 1,
  email: "ana@example.com",
  nombre: "Ana",
  es_admin: false,
  creado_en: "2026-01-01T00:00:00Z",
  nivel: 0,
  plan: { id: "gratis", nombre: "Gratis", nivel: 0, beneficios: [] },
  suscripcion_vence: null,
  limites: { jugadas: 2, historial: 10, chat_por_minuto: 10 },
};

const PLANES = {
  pagos_habilitados: true,
  gratis: { beneficios: ["2 jugadas por juego"] },
  planes: [
    { id: "platinum", nombre: "Platinum", precio: "29.99", moneda: "USD", descripcion: "x", beneficios: ["10 jugadas"], destacado: true, nivel: 2, dias: 30 },
  ],
};

describe("Entrar", () => {
  it("inicia sesión, guarda el token y redirige solo a rutas internas", async () => {
    mockFetch((url) =>
      url.pathname.endsWith("/api/auth/login") ? { body: { token: "tok-1", usuario: PERFIL } } : undefined,
    );
    renderRuta(<Entrar />, { ruta: "/entrar?siguiente=https://malo.example", path: "/entrar" });
    await userEvent.type(screen.getByLabelText(/correo/i), "ana@example.com");
    await userEvent.type(screen.getByLabelText(/contraseña/i), "clave-segura-1");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    await waitFor(() => expect(screen.getByText("otra-ruta")).toBeInTheDocument());
    expect(tokenStore.get()).toBe("tok-1");
  });

  it("muestra el error del servidor", async () => {
    mockFetch(() => ({ status: 401, body: { detail: "Correo o contraseña incorrectos." } }));
    renderRuta(<Entrar />, { ruta: "/entrar", path: "/entrar" });
    await userEvent.type(screen.getByLabelText(/correo/i), "x@example.com");
    await userEvent.type(screen.getByLabelText(/contraseña/i), "nope");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Correo o contraseña incorrectos.");
  });
});

describe("Planes", () => {
  it("sin sesión pide crear cuenta antes de pagar", async () => {
    const spy = mockFetch((url) => (url.pathname.endsWith("/api/pagos/planes") ? { body: PLANES } : undefined));
    renderRuta(<Planes />, { ruta: "/planes", path: "/planes" });
    await userEvent.click(await screen.findByRole("button", { name: /crear cuenta y pagar/i }));
    expect(await screen.findByText("otra-ruta")).toBeInTheDocument();
    expect(spy.mock.calls.some(([u]) => String(u).includes("/ordenes"))).toBe(false);
  });
});

describe("Predicciones", () => {
  it("avisa cuando el plan limita las jugadas", async () => {
    mockFetch((url) =>
      url.pathname.endsWith("/api/predicciones/loto")
        ? {
            body: {
              juego: "loto",
              nombre: "Loto",
              reglas: "6/40",
              historico: { sorteos: 10, desde: "2020-01-01", hasta: "2025-01-01" },
              ultimo_sorteo: { fecha: "2025-01-01", numeros: [1, 2, 3, 4, 5, 6], mas: 1, super_mas: 2 },
              jugadas: [
                { numeros: [1, 9, 17, 25, 33, 40], mas: 3, super_mas: 4, pares: 1, impares: 5 },
                { numeros: [2, 10, 18, 26, 34, 39], mas: 5, super_mas: 6, pares: 5, impares: 1 },
              ],
              aviso: "Aviso",
              solicitadas: 5,
              max_jugadas: 2,
              limitado: true,
              nivel: 0,
            },
          }
        : undefined,
    );
    renderRuta(<Predicciones />, { ruta: "/predicciones", path: "/predicciones" });
    expect(await screen.findByText(/Mostrando 2 de 5 jugadas/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /crear cuenta/i })).toHaveAttribute("href", "/entrar?siguiente=/planes");
  });
});

describe("LoteriaDetalle", () => {
  it("carga el detalle de la lotería de la URL y su pronóstico", async () => {
    const { default: LoteriaDetalle } = await import("./LoteriaDetalle");
    const mapa = Array.from({ length: 100 }, (_, n) => ({
      numero: n, apariciones: n, primer: n, segundo: 0, tercero: 0, ultima_fecha: null, sorteos_sin_salir: 100 - n,
    }));
    const spy = mockFetch((url) => {
      if (url.pathname.endsWith("/pronostico"))
        return {
          body: {
            loteria: "Lotería Nacional", basado_en: { sorteos: 100, hasta: "2025-06-29" },
            jugadas: [{ numeros: [14, 53, 95], pales: [[14, 53], [14, 95], [53, 95]] }],
            calientes: [1, 2, 3, 4, 5], frios: [6, 7, 8, 9, 10], aviso: "Heurístico",
            solicitadas: 5, max_jugadas: 2, limitado: true, nivel: 0,
          },
        };
      if (url.pathname.endsWith("/api/loterias")) return { body: [] };
      if (url.pathname.includes("/api/loterias/"))
        return {
          body: {
            nombre: "Lotería Nacional",
            resumen: { total_sorteos: 100, desde: "2010-01-01", hasta: "2025-06-29", ultimo_sorteo: { fecha: "2025-06-29", loteria: "Lotería Nacional", numeros: [92, 92, 41] }, dias_recientes: 30, mas_frecuente_reciente: { numero: 11, apariciones: 4 }, mas_atrasado: { numero: 12, sorteos_sin_salir: 144, ultima_fecha: "2021-06-24" } },
            ultimos: [], top: [], atrasados: [], combinaciones: [], pales: [{ pale: [30, 93], apariciones: 9 }],
            posiciones: { primer: [], segundo: [], tercero: [] }, mapa, dias_semana: [{ dia: "Lunes", sorteos: 10 }],
          },
        };
      return undefined;
    });
    renderRuta(<LoteriaDetalle />, { ruta: "/loteria/Loter%C3%ADa%20Nacional", path: "/loteria/:nombre" });
    expect(await screen.findByRole("heading", { level: 1, name: "Lotería Nacional" })).toBeInTheDocument();
    expect(await screen.findByText(/Palés: 14-53 · 14-95 · 53-95/)).toBeInTheDocument();
    expect(screen.getByText(/Mostrando 1 de 5 jugadas/)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /^\d\d$/ })).toHaveLength(100);
    expect(spy.mock.calls.some(([u]) => String(u).includes("/api/loterias/Loter%C3%ADa%20Nacional"))).toBe(true);
  });
});
