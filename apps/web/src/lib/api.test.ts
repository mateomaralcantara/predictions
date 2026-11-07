import { describe, expect, it, vi } from "vitest";
import { mockFetch } from "../test/helpers";
import { api, ApiError, buildUrl, SESION_EXPIRADA, tokenStore } from "./api";
import { dos, fecha } from "./format";

describe("buildUrl", () => {
  it("omite parámetros vacíos y codifica valores", () => {
    expect(buildUrl("/api/x", { a: "Lotería Nacional", b: undefined, c: "", d: 0 })).toBe(
      "/backend/api/x?a=Loter%C3%ADa+Nacional&d=0",
    );
  });
});

describe("request", () => {
  it("envía el token y propaga el detalle de error", async () => {
    tokenStore.set("abc");
    const spy = mockFetch(() => ({ status: 409, body: { detail: "Ya existe" } }));
    await expect(api.registro("Ana", "a@b.co", "12345678")).rejects.toThrow("Ya existe");
    const headers = spy.mock.calls[0][1]?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer abc");
  });

  it("borra la sesión y avisa si el servidor responde 401", async () => {
    tokenStore.set("viejo");
    const onExpirada = vi.fn();
    window.addEventListener(SESION_EXPIRADA, onExpirada);
    mockFetch(() => ({ status: 401, body: { detail: "Sesión inválida" } }));
    await expect(api.yo()).rejects.toBeInstanceOf(ApiError);
    expect(tokenStore.get()).toBeNull();
    expect(onExpirada).toHaveBeenCalledOnce();
  });

  it("traduce errores de red a un mensaje claro", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(api.health()).rejects.toThrow(/No se pudo conectar/);
  });
});

describe("format", () => {
  it("formatea números y fechas", () => {
    expect(dos(7)).toBe("07");
    expect(fecha("2025-06-29")).toMatch(/29.*2025/);
    expect(fecha(null)).toBe("—");
  });
});
