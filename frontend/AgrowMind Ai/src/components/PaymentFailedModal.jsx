import { XCircle } from "lucide-react";

export default function PaymentFailedModal() {
  return (
    <div className="paymentModal failed">
      <XCircle size={40} />
      <h2>Payment failed</h2>
      <p>No order was created. Please retry checkout when ready.</p>
    </div>
  );
}
