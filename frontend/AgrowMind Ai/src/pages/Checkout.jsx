import { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

import { useCart } from "../context/CartContext";
import { checkoutCart, createRazorpayOrder } from "../services/authService";

function loadRazorpayScript() {
  return new Promise((resolve) => {
    if (window.Razorpay) {
      resolve(true);
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

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
      if (form.payment_method === "razorpay") {
        const ready = await loadRazorpayScript();
        if (!ready) throw new Error("Could not load Razorpay checkout.");

        const { data: orderData } = await createRazorpayOrder();
        const razorpayOrder = orderData.razorpay_order;

        await new Promise((resolve, reject) => {
          const checkout = new window.Razorpay({
            key: orderData.key_id,
            amount: razorpayOrder.amount,
            currency: razorpayOrder.currency,
            name: "AgroMind AI Marketplace",
            description: "Agriculture product order",
            order_id: razorpayOrder.id,
            prefill: { name: form.full_name, contact: form.mobile },
            handler: async (response) => {
              try {
                const { data } = await checkoutCart({
                  ...form,
                  razorpay_order_id: response.razorpay_order_id,
                  razorpay_payment_id: response.razorpay_payment_id,
                  razorpay_signature: response.razorpay_signature,
                });
                await refreshCart();
                toast.success("Payment verified and order created");
                navigate(`/payment/success?order=${data.order.id}`);
                resolve();
              } catch (err) {
                reject(err);
              }
            },
            modal: { ondismiss: () => reject(new Error("Payment cancelled")) },
          });
          checkout.open();
        });
        return;
      }

      const { data } = await checkoutCart(form);
      await refreshCart();
      toast.success("Order placed");
      navigate(`/payment/success?order=${data.order.id}`);
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Checkout failed");
      if (form.payment_method === "razorpay") navigate("/payment/failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="pageStack">
      <section className="checkoutGrid">
        <form className="panel checkoutForm" onSubmit={submit}>
          <div>
            <span className="eyebrowText">Secure Checkout</span>
            <h1>Shipping and payment</h1>
            <p className="mutedText">Razorpay supports UPI, cards, net banking, and wallets. Orders are created after backend signature verification.</p>
          </div>
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
              <option value="razorpay">Razorpay: UPI / Card / Wallet / Net Banking</option>
            </select>
          </label>
          {error && <div className="alert">{error}</div>}
          <button disabled={loading || cart.items.length === 0} type="submit">{loading ? "Processing..." : "Place Order"}</button>
        </form>
        <aside className="panel orderSummary">
          <h2>Order Summary</h2>
          {cart.items.map((item) => <span key={item.product.id}>{item.product.name} x {item.quantity} - Rs. {item.line_total}</span>)}
          <span>Tax Rs. {cart.tax}</span>
          <span>Shipping Rs. {cart.shipping}</span>
          <strong>Total Rs. {cart.total}</strong>
        </aside>
      </section>
    </main>
  );
}
