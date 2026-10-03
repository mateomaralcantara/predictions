import React, { useCallback, useEffect, useRef, useState } from "react";

type Mensaje = {
  role: "user" | "bot";
  text: string;
};

export default function Chat() {
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [entrada, setEntrada] = useState("");
  const [conectado, setConectado] = useState(false);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const mountedRef = useRef(false);

  const conectar = useCallback(() => {
    if (!mountedRef.current) return;

    const actual = socketRef.current;
    if (
      actual &&
      (actual.readyState === WebSocket.OPEN ||
        actual.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const wsUrl =
      import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8000/ws";

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      console.log("✅ Conectado a WebSocket");
      setConectado(true);
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      setMensajes((prev) => [
        ...prev,
        { role: "bot", text: event.data },
      ]);
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;

      setConectado(false);
      console.warn("⚠️ WebSocket cerrado; reintentando en 3 segundos...");

      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
      }

      reconnectTimerRef.current = window.setTimeout(() => {
        reconnectTimerRef.current = null;
        conectar();
      }, 3000);
    };

    ws.onerror = (error) => {
      if (!mountedRef.current) return;
      console.error("❌ Error en WebSocket:", error);
    };
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    const initialTimer = window.setTimeout(() => {
      conectar();
    }, 0);

    return () => {
      mountedRef.current = false;
      window.clearTimeout(initialTimer);

      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }

      const ws = socketRef.current;
      socketRef.current = null;

      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close(1000, "Componente desmontado");
      }
    };
  }, [conectar]);

  const enviarPregunta = () => {
    const texto = entrada.trim();
    if (!texto) return;

    const ws = socketRef.current;

    if (ws && ws.readyState === WebSocket.OPEN) {
      setMensajes((prev) => [
        ...prev,
        { role: "user", text: texto },
      ]);
      ws.send(texto);
      setEntrada("");
      return;
    }

    console.warn("⚠️ No hay conexión activa; intentando reconectar...");
    conectar();
  };

  return (
    <div className="flex-grow flex flex-col justify-end">
      <div className="text-center mb-2 text-sm">
        {conectado
          ? "🟢 Conectado al servidor"
          : "🔴 Desconectado... intentando reconectar"}
      </div>

      <div className="bg-white/5 p-4 rounded-xl mb-4 max-h-60 overflow-y-auto w-full max-w-4xl mx-auto">
        {mensajes.map((msg, idx) => (
          <div
            key={idx}
            className={`mb-2 ${
              msg.role === "user"
                ? "text-right text-pink-400"
                : "text-left text-blue-400"
            }`}
          >
            <span className="block">{msg.text}</span>
          </div>
        ))}
      </div>

      <div className="flex gap-4 w-full max-w-4xl mx-auto">
        <input
          className="flex-1 px-4 py-2 rounded-lg bg-black/70 border border-white/20 text-white"
          value={entrada}
          onChange={(e) => setEntrada(e.target.value)}
          placeholder="¿Qué número me toca hoy?... (WebSocket real-time)"
          onKeyDown={(e) => e.key === "Enter" && enviarPregunta()}
          disabled={!conectado}
        />
        <button
          className="px-4 py-2 bg-gradient-to-r from-pink-600 to-purple-500 text-white font-bold rounded-xl shadow-md hover:scale-105 transition-all"
          onClick={enviarPregunta}
          disabled={!conectado}
        >
          Preguntar
        </button>
      </div>
    </div>
  );
}
