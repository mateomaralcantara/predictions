# Web · React + Vite + Tailwind

```bash
npm install            # desde la raíz del monorepo
npm run web:dev        # http://localhost:5174  (redirige /backend -> :8000)
```

| Ruta | Página |
|---|---|
| `/` | Resumen, top 10, últimos resultados y asistente |
| `/explorar` | Historial por número, atrasados y ternas |
| `/predicciones` | Jugadas de Loto y SuperKino |
| `/planes` | Planes con pago por PayPal (`/pago/exito`, `/pago/cancelado`) |

La lotería, el número y el juego seleccionados viven en la URL, así que cualquier vista se puede compartir.

Variables (opcionales):

- `VITE_API_URL`: URL pública de la API en producción (por defecto `/backend`).
- `API_PROXY_TARGET`: destino del proxy en desarrollo (por defecto `http://127.0.0.1:8000`).
