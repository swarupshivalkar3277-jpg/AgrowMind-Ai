import { useEffect, useState } from "react";

import { cancelOrder, getOrders } from "../services/authService";
import { downloadPredictionReport } from "../utils/reportPdf";

export default function Orders() {
  const [orders, setOrders] = useState([]);

  async function refresh() {
    const { data } = await getOrders();
    setOrders(data.items || []);
  }

  useEffect(() => {
    refresh().catch(() => setOrders([]));
  }, []);

  async function handleCancel(orderId) {
    await cancelOrder(orderId);
    await refresh();
  }

  return (
    <main className="marketPage">
      <section className="panel">
        <div className="sectionHeader">
          <h1>My Orders</h1>
          <span>{orders.length} orders</span>
        </div>
        <div className="orderList">
          {orders.map((order) => (
            <article className="orderCard" key={order.id}>
              <div>
                <strong>Order #{order.id.slice(-8)}</strong>
                <span>{new Date(order.created_at).toLocaleString()}</span>
                <span>Status: {order.order_status}</span>
                <span>Payment: {order.payment_status}</span>
              </div>
              <div>
                {order.items.map((item) => <span key={item.product.id}>{item.product.name} x {item.quantity}</span>)}
              </div>
              <strong>₹{order.total}</strong>
              <div className="heroActions">
                <button className="secondaryButton" onClick={() => handleCancel(order.id)} type="button">Cancel</button>
                <button
                  className="secondaryButton"
                  onClick={() => downloadPredictionReport({ user: { name: order.address.full_name }, crop: "Marketplace", prediction: { disease: `Invoice ${order.id}`, confidence: order.total, fertilizer: [], treatment: [], irrigation: `Transaction: ${order.transaction_id}` } })}
                  type="button"
                >
                  Invoice
                </button>
              </div>
            </article>
          ))}
          {orders.length === 0 && <p>No orders yet.</p>}
        </div>
      </section>
    </main>
  );
}
