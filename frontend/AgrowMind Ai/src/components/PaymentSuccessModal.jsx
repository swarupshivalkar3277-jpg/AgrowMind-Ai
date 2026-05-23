import { CheckCircle2 } from "lucide-react";

export default function PaymentSuccessModal({ orderId }) {
  return (
    <div className="paymentModal success">
      <CheckCircle2 size={40} />
      <h2>Payment successful</h2>
      <p>Your order {orderId ? `#${orderId.slice(-8)}` : ""} is ready for processing.</p>
    </div>
  );
}
