import { useEffect, useState } from "react";

import OrderCard from "../components/OrderCard";
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
    <main className="pageStack">
      <section className="panel">
        <div className="sectionHeader">
          <div>
            <span className="eyebrowText">Orders</span>
            <h1>My Orders</h1>
          </div>
          <span>{orders.length} orders</span>
        </div>
        <div className="orderList">
          {orders.map((order) => (
            <OrderCard
              key={order.id}
              onCancel={handleCancel}
              onInvoice={() => downloadPredictionReport({ user: { name: order.address.full_name }, crop: "Marketplace", prediction: { disease: `Invoice ${order.id}`, confidence: order.total, fertilizer: [], treatment: [], irrigation: `Transaction: ${order.transaction_id}` } })}
              order={order}
            />
          ))}
          {orders.length === 0 && <p>No orders yet.</p>}
        </div>
      </section>
    </main>
  );
}
