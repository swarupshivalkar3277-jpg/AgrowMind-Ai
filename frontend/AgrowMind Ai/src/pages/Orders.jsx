import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShoppingBag } from "lucide-react";

import EmptyState from "../components/EmptyState";
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
          {orders.length === 0 && (
            <EmptyState
              action={<Link className="primaryButton" to="/marketplace">Browse Marketplace</Link>}
              icon={ShoppingBag}
              title="No orders yet"
              text="Your paid, processing, shipped, and delivered marketplace orders will appear here."
            />
          )}
        </div>
      </section>
    </main>
  );
}
