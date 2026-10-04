export default function PaypalButton() {
  const handlePayment = async () => {
    const res = await fetch("http://localhost:8000/paypal/create-order", {
      method: "POST",
    });
    const data = await res.json();
    const approveLink = data.links.find((link) => link.rel === "approve");
    window.location.href = approveLink.href;
  };

  return (
    <button
      className="px-6 py-3 bg-yellow-400 text-black font-bold rounded-xl shadow hover:scale-105 transition-all"
      onClick={handlePayment}
    >
      💰 Comprar Predicción Premium
    </button>
  );
}
