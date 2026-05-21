import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useCart } from "../context/CartContext";
import { checkoutCart } from "../services/authService";

export default function Checkout() {
  const { cart, refreshCart } = useCart();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    full_name: "",
    mobile: "",
    address: "",
    state: "",
    district: "",
    pin_code: "",
    payment_method: "cash_on_delivery",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { data } = await checkoutCart(form);
      await refreshCart();
      navigate(`/payment/success?order=${data.order.id}`);
    } catch (err) {
      setError(err?.response?.data?.detail || "Checkout failed");
      navigate("/payment/failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="marketPage">
      <section className="checkoutGrid">
        <form className="panel checkoutForm" onSubmit={submit}>
          <h1>Checkout</h1>
          {["full_name", "mobile", "address", "state", "district", "pin_code"].map((field) => (
            <label key={field}>
              <span>{field.replaceAll("_", " ")}</span>
              <input onChange={(event) => update(field, event.target.value)} required value={form[field]} />
            </label>
          ))}
          <label>
            <span>Payment method</span>
            <select onChange={(event) => update("payment_method", event.target.value)} value={form.payment_method}>
              <option value="cash_on_delivery">Cash on Delivery</option>
              <option value="upi">UPI</option>
              <option value="card">Credit/Debit Card</option>
              <option value="razorpay">Razorpay verified payment</option>
            </select>
          </label>
          {error && <div className="alert">{error}</div>}
          <button disabled={loading || cart.items.length === 0} type="submit">{loading ? "Placing order..." : "Place Order"}</button>
        </form>
        <aside className="panel orderSummary">
          <h2>Order Summary</h2>
          {cart.items.map((item) => (
            <span key={item.product.id}>{item.product.name} x {item.quantity} - ₹{item.line_total}</span>
          ))}
          <strong>Total ₹{cart.total}</strong>
        </aside>
      </section>
    </main>
  );
}
