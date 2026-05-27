import { RotateCcw, Star, Truck } from "lucide-react";
import { Link } from "react-router-dom";

const steps = ["ORDER_PLACED", "PAYMENT_SUCCESS", "PROCESSING", "PACKED", "SHIPPED", "OUT_FOR_DELIVERY", "DELIVERED"];
const cancellable = ["ORDER_PLACED", "PAYMENT_PENDING", "PAYMENT_SUCCESS", "PROCESSING"];
const refundable = ["PAYMENT_SUCCESS", "PROCESSING", "PACKED", "SHIPPED", "OUT_FOR_DELIVERY", "DELIVERED"];

export default function OrderCard({ order, onCancel, onInvoice, onRefund }) {
  const canCancel = cancellable.includes(order.order_status);
  const canRefund = order.payment_method === "razorpay" && order.payment_status === "paid" && refundable.includes(order.order_status);
  const firstItem = order.items?.[0];
  const product = firstItem?.product || {};
  const activeIndex = Math.max(0, steps.indexOf(order.order_status));

  return (
    <article className="orderCard premiumOrderCard">
      <div className="orderProductThumb">
        {product.image ? <img alt={product.name} src={product.image} /> : <Truck size={28} />}
      </div>
      <div className="orderMain">
        <div className="orderTopLine">
          <div>
            <strong>Order #{order.id.slice(-8)}</strong>
            <span>{new Date(order.created_at).toLocaleString()} - {order.items.length} item(s)</span>
          </div>
          <span className="softBadge">{order.order_status.replaceAll("_", " ")}</span>
        </div>
        <strong>{product.name || "Marketplace order"}</strong>
        <div className="orderTrack">
          {steps.map((step, index) => (
            <span className={index <= activeIndex ? "done" : ""} key={step}>{step.replaceAll("_", " ")}</span>
          ))}
        </div>
        {order.tracking?.length > 0 && <small>{order.tracking[order.tracking.length - 1].message}</small>}
        <div className="orderMetaRow">
          <span>Rs. {order.total}</span>
          <span>{order.payment_method}</span>
          <span>{order.transaction_id || "Tracking pending"}</span>
        </div>
      </div>
      <div className="orderActions">
        <Link className="secondaryButton" to={`/orders?track=${order.id}`}>Track</Link>
        <button className="secondaryButton" type="button"><RotateCcw size={16} /> Reorder</button>
        <button className="secondaryButton" type="button"><Star size={16} /> Review</button>
        {canCancel && <button className="secondaryButton" onClick={() => onCancel(order.id)} type="button">Cancel</button>}
        {canRefund && <button className="secondaryButton" onClick={() => onRefund(order.id)} type="button">Refund</button>}
        <button className="secondaryButton" onClick={() => onInvoice(order)} type="button">Invoice</button>
      </div>
    </article>
  );
}
