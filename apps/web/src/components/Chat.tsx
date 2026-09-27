import React, { useEffect, useState, useRef, useCallback } from "react";

type Mensaje = {
  role: "user" | "bot";
  text: string;
};

export default function Chat() {
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [entrada, setEntrada] = useState("");
  const [conectado, setConectado] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  // ✅ Función conectar usando useCallback (para que no de errores)
  const conectar = useCallback(() => {
    const wsUrl = import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8000/ws";
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      console.log("✅ Conectado a WebSocket");
      setConectado(true);
    };

    ws.onmessage = (event) => {
      setMensajes((prev) => [...prev, { role: "bot", text: event.data }]);
    };

    ws.onclose = (event) => {
      console.warn("⚠️ WebSocket cerrado, intentando reconectar...", event);
      setConectado(false);

      // 🔄 Intentar reconectar después de 3 segundos
      setTimeout(() => {
        console.log("🔄 Reintentando conexión WebSocket...");
        conectar();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error("❌ Error en WebSocket:", error);
      ws.close();
    };
  }, []);

  // ✅ useEffect con dependencia correcta
  useEffect(() => {
    conectar();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [conectar]);

  // ✅ Función para enviar mensajes solo si estamos conectados
  const enviarPregunta = () => {
    if (!entrada.trim()) return;

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      setMensajes((prev) => [...prev, { role: "user", text: entrada }]);
      socketRef.current.send(entrada);
      setEntrada("");
    } else {
      console.warn("⚠️ No hay conexión activa, intentando reconectar...");
      conectar();
    }
  };

  return (
    <div className="flex-grow flex flex-col justify-end">
      <div className="text-center mb-2 text-sm">
        {conectado ? "🟢 Conectado al servidor" : "🔴 Desconectado... intentando reconectar"}
      </div>

      <div className="bg-white/5 p-4 rounded-xl mb-4 max-h-60 overflow-y-auto w-full max-w-4xl mx-auto">
        {mensajes.map((msg, idx) => (
          <div key={idx} className={`mb-2 ${msg.role === "user" ? "text-right text-pink-400" : "text-left text-blue-400"}`}>
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
