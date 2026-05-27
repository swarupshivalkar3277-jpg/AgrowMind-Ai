import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, CreditCard, MapPin, PackageCheck, ShieldCheck, Truck } from "lucide-react";
import toast from "react-hot-toast";

import { useCart } from "../context/CartContext";
import { checkoutCart, createRazorpayOrder, verifyRazorpayPayment } from "../services/authService";

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

function checkoutErrorMessage(error) {
  const payload = error?.response?.data;
  const detail = payload?.detail || payload?.error;

  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join(", ");
  return error?.message || "Checkout failed";
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
    location_lat: "",
    location_lng: "",
    location_label: "",
    payment_method: "cash_on_delivery",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function useLiveLocation() {
    if (!navigator.geolocation) {
      setError("Live location is not supported on this device.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setForm((current) => ({
          ...current,
          location_lat: position.coords.latitude,
          location_lng: position.coords.longitude,
          location_label: `Lat ${position.coords.latitude.toFixed(5)}, Lng ${position.coords.longitude.toFixed(5)}`,
        }));
      },
      () => setError("Could not access live location. Please allow location permission.")
    );
  }

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const payload = {
      ...form,
      location_lat: form.location_lat === "" ? null : Number(form.location_lat),
      location_lng: form.location_lng === "" ? null : Number(form.location_lng),
    };
    try {
      if (form.payment_method === "razorpay") {
        const ready = await loadRazorpayScript();
        if (!ready) throw new Error("Could not load Razorpay checkout.");

        const { data: orderData } = await createRazorpayOrder({ ...payload, payment_method: "razorpay" });
        const payment = orderData.data || {};

        await new Promise((resolve, reject) => {
          const checkout = new window.Razorpay({
            key: payment.razorpay_key,
            amount: payment.amount,
            currency: payment.currency,
            name: "AgroMind AI Marketplace",
            description: "Agriculture product order",
            order_id: payment.razorpay_order_id,
            prefill: { name: form.full_name, contact: form.mobile },
            handler: async (response) => {
              try {
                const { data } = await verifyRazorpayPayment({
                  razorpay_order_id: response.razorpay_order_id,
                  razorpay_payment_id: response.razorpay_payment_id,
                  razorpay_signature: response.razorpay_signature,
                });
                await refreshCart();
                toast.success("Payment verified and order created");
                navigate(`/payment/success?order=${data.data?.order?.id || data.order?.id || ""}`);
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

      const { data } = await checkoutCart(payload);
      await refreshCart();
      toast.success("Order placed with Cash on Delivery");
      navigate(`/payment/success?order=${data.order.id}&method=cod`);
    } catch (err) {
      setError(checkoutErrorMessage(err));
      if (form.payment_method === "razorpay") navigate("/payment/failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="pageStack shopAccountPage">
      <section className="shopPageHeader">
        <div><span>Secure Checkout</span><h1>Complete your order</h1></div>
      </section>
      <section className="checkoutSteps" aria-label="Checkout progress">
        {["Address", "Delivery", "Payment", "Confirmation"].map((step, index) => <span className={index === 0 ? "active" : ""} key={step}><CheckCircle2 size={17} /> {step}</span>)}
      </section>
      <section className="checkoutGrid premiumCheckout">
        <form className="panel checkoutForm" onSubmit={submit}>
          <div>
            <span className="eyebrowText">Secure Checkout</span>
            <h1>Shipping and payment</h1>
            <p className="mutedText">Razorpay supports UPI, cards, net banking, and wallets. Orders are created after backend signature verification.</p>
          </div>
          <div className="checkoutBlockTitle"><MapPin size={18} /><strong>Step 1: Address</strong></div>
          {["full_name", "mobile", "address", "state", "district", "pin_code"].map((field) => (
            <label key={field}>
              <span>{field.replaceAll("_", " ")}</span>
              <input onChange={(event) => update(field, event.target.value)} required value={form[field]} />
            </label>
          ))}
          <div className="locationBox">
            <div>
              <strong>Delivery location</strong>
              <span>{form.location_label || "Optional: share live location for easier delivery."}</span>
            </div>
            <button className="secondaryButton" onClick={useLiveLocation} type="button">Use Live Location</button>
          </div>
          <div className="checkoutBlockTitle"><Truck size={18} /><strong>Step 2: Delivery</strong><span>Standard delivery in 2-5 days</span></div>
          <div className="checkoutBlockTitle"><CreditCard size={18} /><strong>Step 3: Payment</strong></div>
          <label>
            <span>Payment method</span>
            <select onChange={(event) => update("payment_method", event.target.value)} value={form.payment_method}>
              <option value="cash_on_delivery">Cash on Delivery</option>
              <option value="razorpay">Razorpay: UPI / Card / Wallet / Net Banking</option>
            </select>
          </label>
          {error && <div className="alert">{error}</div>}
          <button className="primaryButton" disabled={loading || cart.items.length === 0 || cart.items.some((item) => item.product.stock <= 0 || item.quantity > item.product.stock)} type="submit">
            {loading ? "Processing..." : "Place Order"}
          </button>
        </form>
        <aside className="panel orderSummary premiumSummary">
          <p><ShieldCheck size={16} /> Payment verified by backend before order creation.</p>
          <h2>Order Summary</h2>
          {cart.items.length === 0 && <span>Your cart is empty.</span>}
          {cart.items.map((item) => (
            <span key={item.product.id}>
              {item.product.name} x {item.quantity} - Rs. {item.line_total}
              {item.product.unit_size ? ` (${item.product.unit_size})` : ""}
              {item.product.stock <= 0 ? " (Out of Stock)" : item.quantity > item.product.stock ? " (Stock unavailable)" : ""}
            </span>
          ))}
          <span>Tax Rs. {cart.tax}</span>
          <span>Shipping Rs. {cart.shipping}</span>
          <strong><PackageCheck size={18} /> Total Rs. {cart.total}</strong>
        </aside>
      </section>
    </main>
  );
}
