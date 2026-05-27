import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ShoppingBag } from "lucide-react";

import EmptyState from "../components/EmptyState";
import OrderCard from "../components/OrderCard";
import { cancelOrder, getOrders, requestOrderRefund } from "../services/authService";
import { downloadPredictionReport } from "../utils/reportPdf";

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [status, setStatus] = useState("all");
  const [loading, setLoading] = useState(true);
  const [params] = useSearchParams();

  async function refresh() {
    try {
      const { data } = await getOrders();
      setOrders(data.items || []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh().catch(() => setOrders([]));
  }, []);

  const filtered = useMemo(() => {
    if (status === "all") return orders;
    return orders.filter((order) => order.order_status === status);
  }, [orders, status]);

  const trackedOrder = orders.find((order) => order.id === params.get("track"));

  async function handleCancel(orderId) {
    await cancelOrder(orderId);
    await refresh();
  }

  async function handleRefund(orderId) {
    await requestOrderRefund(orderId);
    await refresh();
  }

  return (
    <main className="pageStack shopAccountPage">
      <section className="panel ordersPanel">
        <div className="sectionHeader">
          <div>
            <span className="eyebrowText">Orders</span>
            <h1>My Orders</h1>
          </div>
          <span>{orders.length} orders</span>
        </div>
        <div className="orderFilters">
          {["all", "ORDER_PLACED", "SHIPPED", "DELIVERED", "CANCELLED", "REFUNDED"].map((item) => (
            <button className={status === item ? "active" : ""} key={item} onClick={() => setStatus(item)} type="button">{item.replaceAll("_", " ")}</button>
          ))}
        </div>
        {trackedOrder && (
          <section className="trackingPanel">
            <h2>Tracking #{trackedOrder.id.slice(-8)}</h2>
            <div className="trackingTimeline">
              {(trackedOrder.status_history || trackedOrder.tracking || []).map((item, index) => (
                <span className="done" key={`${item.status}-${index}`}><strong>{item.status.replaceAll("_", " ")}</strong><small>{item.message}</small></span>
              ))}
            </div>
            <p>Courier details and delivery partner information will appear after shipment is assigned.</p>
          </section>
        )}
        <div className="orderList">
          {loading && Array.from({ length: 3 }).map((_, index) => <div className="orderSkeleton" key={index} />)}
          {!loading && filtered.map((order) => (
            <OrderCard
              key={order.id}
              onCancel={handleCancel}
              onInvoice={() => downloadPredictionReport({ user: { name: order.address.full_name }, crop: "Marketplace", prediction: { disease: `Invoice ${order.id}`, confidence: order.total, fertilizer: [], treatment: [], irrigation: `Transaction: ${order.transaction_id}` } })}
              onRefund={handleRefund}
              order={order}
            />
          ))}
          {!loading && filtered.length === 0 && (
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
