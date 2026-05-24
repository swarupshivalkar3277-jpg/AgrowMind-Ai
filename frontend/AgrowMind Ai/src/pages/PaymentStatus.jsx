import { Link, useLocation } from "react-router-dom";

import PaymentFailedModal from "../components/PaymentFailedModal";
import PaymentSuccessModal from "../components/PaymentSuccessModal";

export default function PaymentStatus({ success }) {
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const order = params.get("order");
  const method = params.get("method");

  return (
    <main className="pageStack">
      <section className="panel paymentState">
        {success ? <PaymentSuccessModal method={method} orderId={order} /> : <PaymentFailedModal />}
        <div className="heroActions">
          <Link className="primaryButton" to="/orders">My Orders</Link>
          <Link className="secondaryButton" to="/marketplace">Marketplace</Link>
        </div>
      </section>
    </main>
  );
}
