import { useEffect, useState } from "react";
import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function NumerosSalidores() {
  const [numeros, setNumeros] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get(
          `${API_BASE_URL}/api/numeros-mas-salidores`
        );
        setNumeros(res.data);
      } catch (error) {
        console.error("Error al obtener los números:", error);
      }
    };

    fetchData();
  }, []);

  return (
    <div className="bg-black p-4 rounded-lg shadow-lg border border-green-500 text-white">
      <h2 className="text-2xl font-bold mb-4 text-green-400">
        Top 10 Números Más Salidores (Nacional)
      </h2>
      <ul className="grid grid-cols-2 gap-2">
        {numeros.map((n, i) => (
          <li key={i} className="bg-gray-800 p-2 rounded text-center">
            <span className="text-green-300 font-semibold text-lg">
              #{n.numero}
            </span>
            <div className="text-sm text-gray-400">
              {n.apariciones} veces
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
