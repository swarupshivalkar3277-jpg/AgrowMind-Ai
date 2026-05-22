import { Link, useLocation } from "react-router-dom";

import PaymentFailedModal from "../components/PaymentFailedModal";
import PaymentSuccessModal from "../components/PaymentSuccessModal";

export default function PaymentStatus({ success }) {
  const location = useLocation();
  const order = new URLSearchParams(location.search).get("order");

  return (
    <main className="pageStack">
      <section className="panel paymentState">
        {success ? <PaymentSuccessModal orderId={order} /> : <PaymentFailedModal />}
        <div className="heroActions">
          <Link className="primaryButton" to="/orders">My Orders</Link>
          <Link className="secondaryButton" to="/marketplace">Marketplace</Link>
        </div>
      </section>
    </main>
  );
}
