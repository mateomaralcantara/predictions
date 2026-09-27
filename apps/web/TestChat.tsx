import React, { useEffect } from "react";

export default function TestChat() {
  useEffect(() => {
    const testChat = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ prompt: "Dime el número de la suerte para hoy" }),
        });

        const data = await res.json();
        console.log("🧠 Respuesta del backend:", data);
        alert(`Respuesta del bot: ${data.respuesta}`);
      } catch (err) {
        console.error("❌ Error al llamar a /chat:", err);
        alert("❌ Error al conectar con el backend");
      }
    };

    testChat();
  }, []);

  return (
    <div className="p-4 text-white">
      <h2 className="text-2xl font-bold">Test de conexión con OpenAI</h2>
      <p className="mt-2">Mira la consola o espera el alert 👀</p>
    </div>
  );
}
