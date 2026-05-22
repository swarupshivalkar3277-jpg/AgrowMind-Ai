import { CheckCircle2 } from "lucide-react";

export default function PaymentSuccessModal({ orderId }) {
  return (
    <div className="paymentModal success">
      <CheckCircle2 size={40} />
      <h2>Payment successful</h2>
      <p>Your order {orderId ? `#${orderId.slice(-8)}` : ""} has been confirmed.</p>
    </div>
  );
}
