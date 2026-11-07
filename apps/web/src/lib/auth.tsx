import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, type Perfil, SESION_EXPIRADA, tokenStore } from "./api";

interface AuthState {
  usuario: Perfil | null;
  cargando: boolean;
  entrar: (email: string, password: string) => Promise<void>;
  registrarse: (nombre: string, email: string, password: string) => Promise<void>;
  salir: () => void;
  refrescar: () => Promise<void>;
  setUsuario: (p: Perfil) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Perfil | null>(null);
  const [cargando, setCargando] = useState(() => !!tokenStore.get());

  const refrescar = useCallback(async () => {
    if (!tokenStore.get()) {
      setUsuario(null);
      setCargando(false);
      return;
    }
    try {
      setUsuario(await api.yo());
    } catch {
      setUsuario(null);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void refrescar();
    const onExpirada = () => setUsuario(null);
    window.addEventListener(SESION_EXPIRADA, onExpirada);
    return () => window.removeEventListener(SESION_EXPIRADA, onExpirada);
  }, [refrescar]);

  const value = useMemo<AuthState>(
    () => ({
      usuario,
      cargando,
      refrescar,
      setUsuario,
      async entrar(email, password) {
        const s = await api.login(email, password);
        tokenStore.set(s.token);
        setUsuario(s.usuario);
      },
      async registrarse(nombre, email, password) {
        const s = await api.registro(nombre, email, password);
        tokenStore.set(s.token);
        setUsuario(s.usuario);
      },
      salir() {
        tokenStore.set(null);
        setUsuario(null);
      },
    }),
    [usuario, cargando, refrescar],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
