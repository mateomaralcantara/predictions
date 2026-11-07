import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { AuthProvider } from "./lib/auth";
import "./index.css";
import Cuenta from "./pages/Cuenta";
import Entrar from "./pages/Entrar";
import Explorar from "./pages/Explorar";
import Inicio from "./pages/Inicio";
import { NoEncontrado, PagoCancelado, PagoExito } from "./pages/Pago";
import Planes from "./pages/Planes";
import Predicciones from "./pages/Predicciones";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Inicio />} />
          <Route path="explorar" element={<Explorar />} />
          <Route path="predicciones" element={<Predicciones />} />
          <Route path="planes" element={<Planes />} />
          <Route path="membresias" element={<Planes />} />
          <Route path="entrar" element={<Entrar />} />
          <Route path="cuenta" element={<Cuenta />} />
          <Route path="pago/exito" element={<PagoExito />} />
          <Route path="pago/cancelado" element={<PagoCancelado />} />
          <Route path="*" element={<NoEncontrado />} />
        </Route>
      </Routes>
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
);
