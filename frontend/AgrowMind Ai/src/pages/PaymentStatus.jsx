import { Link, useLocation } from "react-router-dom";

export default function PaymentStatus({ success }) {
  const location = useLocation();
  const order = new URLSearchParams(location.search).get("order");

  return (
    <main className="marketPage">
      <section className="panel paymentState">
        <p className="eyebrow">{success ? "Payment Success" : "Payment Failed"}</p>
        <h1>{success ? "Order confirmed" : "We could not place the order"}</h1>
        {order && <p>Order ID: {order}</p>}
        <div className="heroActions">
          <Link className="primaryButton" to="/orders">My Orders</Link>
          <Link className="secondaryButton" to="/marketplace">Marketplace</Link>
        </div>
      </section>
    </main>
  );
}
