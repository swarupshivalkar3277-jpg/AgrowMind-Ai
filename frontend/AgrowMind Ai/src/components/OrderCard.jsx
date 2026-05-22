export default function OrderCard({ order, onCancel, onInvoice }) {
  return (
    <article className="orderCard">
      <div>
        <strong>Order #{order.id.slice(-8)}</strong>
        <span>{new Date(order.created_at).toLocaleString()}</span>
        <span>{order.items.length} item(s)</span>
      </div>
      <div className="statusRail">
        <span>{order.order_status}</span>
        <small>{order.payment_status}</small>
      </div>
      <strong>Rs. {order.total}</strong>
      <div className="heroActions">
        <button className="secondaryButton" onClick={() => onCancel(order.id)} type="button">Cancel</button>
        <button className="secondaryButton" onClick={() => onInvoice(order)} type="button">Invoice</button>
      </div>
    </article>
  );
}
