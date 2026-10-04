import React from "react";

const planes = [
  {
    name: "⭐ Explorador Cósmico",
    price: "$9.99",
    description: "Perfecto para principiantes curiosos.",
    features: [
      "500 predicciones mágicas",
      "100 análisis místico programado",
      "Análisis predictivos con software especializado",
    ],
  },
  {
    name: "🔥 Plan Platinum",
    price: "$29.99",
    description: "Ideal para jugadores comprometidos.",
    features: [
      "Todo lo del plan normal",
      "Análisis predictivos ilimitados",
      "Triangulación matemática",
      "Plan mensual de predicciones",
      "Gráficos avanzados",
      "Algoritmos de limpieza de datos",
    ],
  },
  {
    name: "👑 Oráculo Supremo",
    price: "$59.99",
    description: "Para los pros que van por el millón 🔮",
    features: [
      "Todo lo del plan platinum",
      "Eventos en vivo",
      "Mentoría personalizada",
      "Acceso a herramientas premium",
    ],
  },
];

export default function MembershipPlans() {
  return (
    <div className="mt-16 w-full max-w-6xl mx-auto grid gap-8 md:grid-cols-3 text-white">
      {planes.map((plan, index) => (
        <div key={index} className="bg-gray-800 rounded-2xl p-6 shadow-lg">
          <h2 className="text-xl font-bold mb-2">{plan.name}</h2>
          <p className="text-4xl font-bold mb-4">{plan.price}</p>
          <p className="mb-4 italic text-gray-300">{plan.description}</p>
          <ul className="mb-4 space-y-2 text-left">
            {plan.features.map((feature, i) => (
              <li key={i} className="flex items-start">
                <span className="mr-2 text-green-400">✓</span>
                <span>{feature}</span>
              </li>
            ))}
          </ul>
          <button
            onClick={() => alert(`Compraste: ${plan.name}`)}
            className="w-full bg-indigo-600 hover:bg-indigo-700 py-2 px-4 rounded-full font-bold"
          >
            Comprar predicción
          </button>
        </div>
      ))}
    </div>
  );
}
