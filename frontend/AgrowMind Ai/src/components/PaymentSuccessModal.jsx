import { CheckCircle2 } from "lucide-react";

export default function PaymentSuccessModal({ method, orderId }) {
  const isCod = method === "cod";
  return (
    <div className="paymentModal success">
      <CheckCircle2 size={40} />
      <h2>{isCod ? "Order placed" : "Payment successful"}</h2>
      <p>{isCod ? "Cash on Delivery selected." : "Your payment is verified."} Your order {orderId ? `#${orderId.slice(-8)}` : ""} is ready for tracking.</p>
    </div>
  );
}
