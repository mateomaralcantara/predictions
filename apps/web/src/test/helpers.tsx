import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";
import { AuthProvider } from "../lib/auth";

type Handler = (url: URL, init?: RequestInit) => { status?: number; body: unknown } | undefined;

/** Sustituye fetch por un enrutador de respuestas falsas. */
export function mockFetch(handler: Handler) {
  const spy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://test");
    const r = handler(url, init) ?? { status: 404, body: { detail: "no mock" } };
    return new Response(JSON.stringify(r.body), {
      status: r.status ?? 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", spy);
  return spy;
}

export function renderRuta(ui: ReactElement, { ruta = "/", path = "/" } = {}) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path={path} element={ui} />
          <Route path="*" element={<div>otra-ruta</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}
