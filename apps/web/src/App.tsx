import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import PaypalButton from "./components/PaypalButton";
import Chat from "./components/Chat";
import NumerosSalidores from "./components/NumerosSalidores";

export default function App() {
  const [menuAbierto, setMenuAbierto] = useState(false);
  const [mostrarSuscripcion, setMostrarSuscripcion] = useState(false);
  const [mostrarLogin, setMostrarLogin] = useState(false);
  const navigate = useNavigate();

  return (
    <main
      className="min-h-screen flex flex-col px-4 py-10"
      style={{
        background: "linear-gradient(to bottom right, #000000, #1a1a1a)",
        color: "#ffffff",
        fontFamily: "Segoe UI, sans-serif",
      }}
    >
      {/* Menú desplegable */}
      <div className="absolute top-4 right-4 z-50">
        <div className="relative inline-block text-left">
          <button
            onClick={() => setMenuAbierto(!menuAbierto)}
            className="flex items-center justify-center w-10 h-10 bg-gray-800 rounded-full text-white hover:bg-gray-700 focus:outline-none"
          >
            ☰
          </button>
          {menuAbierto && (
            <div className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-white ring-opacity-10 focus:outline-none">
              <div className="py-1 text-black">
                <button
                  className="block w-full text-left px-4 py-2 hover:bg-gray-100"
                  onClick={() => {
                    setMostrarSuscripcion(true);
                    setMostrarLogin(false);
                  }}
                >
                  Suscribirse
                </button>
                <button
                  className="block w-full text-left px-4 py-2 hover:bg-gray-100"
                  onClick={() => {
                    setMostrarLogin(true);
                    setMostrarSuscripcion(false);
                  }}
                >
                  Iniciar Sesión
                </button>
                <button
                  className="block w-full text-left px-4 py-2 hover:bg-gray-100"
                  onClick={() => navigate("/membresias")}
                >
                  Membresías
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Formulario de Suscripción */}
      {mostrarSuscripcion && (
        <div className="max-w-md mx-auto bg-white text-black rounded-xl p-6 mt-16">
          <h2 className="text-2xl font-bold mb-4">Suscribirse</h2>
          <form className="space-y-4">
            <input type="text" placeholder="Nombres" className="w-full p-2 border rounded" />
            <input type="text" placeholder="Apellidos" className="w-full p-2 border rounded" />
            <input type="email" placeholder="Correo" className="w-full p-2 border rounded" />
            <input type="tel" placeholder="Teléfono" className="w-full p-2 border rounded" />
            <input type="text" placeholder="País" className="w-full p-2 border rounded" />
            <button type="submit" className="w-full bg-blue-600 text-white p-2 rounded">Enviar</button>
          </form>
        </div>
      )}

      {/* Formulario de Login */}
      {mostrarLogin && (
        <div className="max-w-md mx-auto bg-white text-black rounded-xl p-6 mt-16">
          <h2 className="text-2xl font-bold mb-4">Iniciar Sesión</h2>
          <form className="space-y-4">
            <input type="email" placeholder="Correo" className="w-full p-2 border rounded" />
            <input type="password" placeholder="Contraseña" className="w-full p-2 border rounded" />
            <button type="submit" className="w-full bg-blue-600 text-white p-2 rounded">Entrar</button>
          </form>
        </div>
      )}

      {/* Título y tarjetas */}
      <div>
        <h1 className="text-4xl md:text-5xl font-extrabold mb-6 text-center" style={{ textShadow: "0 0 10px #ff00cc, 0 0 20px #3333ff" }}>
          🔥 Arregla tu Suerte 🔮
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-4xl mx-auto mb-6">
          {[{ label: "Último número", valor: "90" }, { label: "Frecuente hoy", valor: "14" }, { label: "Recomendado", valor: "23" }].map((card, index) => (
            <div key={index} className="backdrop-blur-md bg-white/5 border border-white/10 p-4 rounded-2xl shadow-lg text-center">
              <h2 className="text-lg font-semibold mb-1">{card.label}</h2>
              <p className="text-4xl font-bold" style={{ color: "#39FF14", textShadow: "0 0 10px #39FF14" }}>
                {card.valor}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Componente del Chat */}
      <Chat />

      {/* Componente de Números Salidores */}
      <div className="mt-10">
        <NumerosSalidores />
      </div>

      {/* Botón de PayPal */}
      <div className="mt-10 w-full max-w-4xl mx-auto text-center">
        <PaypalButton />
      </div>
    </main>
  );
}
