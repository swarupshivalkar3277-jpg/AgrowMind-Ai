const steps = ["pending", "paid", "processing", "shipped", "delivered"];

export default function OrderCard({ order, onCancel, onInvoice, onRefund }) {
  const canCancel = ["pending", "paid", "processing"].includes(order.order_status);
  const canRefund = order.payment_method === "razorpay" && order.payment_status === "paid" && ["paid", "processing", "shipped", "delivered"].includes(order.order_status);

  return (
    <article className="orderCard">
      <div>
        <strong>Order #{order.id.slice(-8)}</strong>
        <span>{new Date(order.created_at).toLocaleString()}</span>
        <span>{order.items.length} item(s)</span>
        <div className="orderTrack">
          {steps.map((step) => (
            <span className={steps.indexOf(step) <= steps.indexOf(order.order_status) ? "done" : ""} key={step}>{step}</span>
          ))}
        </div>
        {order.tracking?.length > 0 && <small>{order.tracking[order.tracking.length - 1].message}</small>}
      </div>
      <div className="statusRail">
        <span>{order.order_status}</span>
        <small>{order.payment_status}</small>
      </div>
      <strong>Rs. {order.total}</strong>
      <div className="heroActions">
        {canCancel && <button className="secondaryButton" onClick={() => onCancel(order.id)} type="button">Cancel</button>}
        {canRefund && <button className="secondaryButton" onClick={() => onRefund(order.id)} type="button">Refund</button>}
        <button className="secondaryButton" onClick={() => onInvoice(order)} type="button">Invoice</button>
      </div>
    </article>
  );
}
