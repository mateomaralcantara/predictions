import { Bot, Send } from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

type Mensaje = { role: "user" | "bot"; text: string; error?: boolean };

const SUGERENCIAS = [
  "Top 10 números de la Nacional",
  "Últimos 5 resultados de Leidsa",
  "¿Cuándo salió el 23?",
  "Números más atrasados de Loteka",
];

export default function Chat() {
  const [mensajes, setMensajes] = useState<Mensaje[]>([
    { role: "bot", text: "¡Hola! Pregúntame por números, fechas o loterías del histórico." },
  ]);
  const [entrada, setEntrada] = useState("");
  const [enviando, setEnviando] = useState(false);
  const listaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listaRef.current?.scrollTo({ top: listaRef.current.scrollHeight, behavior: "smooth" });
  }, [mensajes]);

  async function enviar(texto: string) {
    const pregunta = texto.trim();
    if (!pregunta || enviando) return;
    setMensajes((m) => [...m, { role: "user", text: pregunta }]);
    setEntrada("");
    setEnviando(true);
    try {
      const r = await api.chat(pregunta);
      setMensajes((m) => [...m, { role: "bot", text: r.respuesta }]);
    } catch (e) {
      setMensajes((m) => [...m, { role: "bot", text: e instanceof Error ? e.message : "Error", error: true }]);
    } finally {
      setEnviando(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void enviar(entrada);
  }

  return (
    <section className="card flex h-full min-w-0 flex-col" aria-labelledby="chat-title">
      <h2 id="chat-title" className="card-title mb-3 flex items-center gap-2">
        <Bot className="h-4 w-4" aria-hidden /> Asistente
      </h2>

      <div ref={listaRef} className="mb-3 h-72 flex-1 space-y-2 overflow-y-auto pr-1" aria-live="polite">
        {mensajes.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] whitespace-pre-line rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                m.role === "user"
                  ? "rounded-br-sm bg-emerald-500 text-ink-950"
                  : m.error
                    ? "rounded-bl-sm border border-rose-500/30 bg-rose-500/10 text-rose-200"
                    : "rounded-bl-sm bg-ink-800 text-slate-200"
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {enviando && <div className="text-xs text-slate-500">Pensando…</div>}
      </div>

      <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
        {SUGERENCIAS.map((s) => (
          <button
            key={s}
            type="button"
            className="chip border-white/10 text-slate-300 hover:border-emerald-400/50 hover:text-white"
            onClick={() => void enviar(s)}
            disabled={enviando}
          >
            {s}
          </button>
        ))}
      </div>

      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          className="input"
          value={entrada}
          onChange={(e) => setEntrada(e.target.value)}
          placeholder="Escribe tu pregunta…"
          maxLength={500}
          aria-label="Pregunta"
        />
        <button className="btn-primary" disabled={enviando || !entrada.trim()} aria-label="Enviar">
          <Send className="h-4 w-4" aria-hidden />
        </button>
      </form>
    </section>
  );
}
