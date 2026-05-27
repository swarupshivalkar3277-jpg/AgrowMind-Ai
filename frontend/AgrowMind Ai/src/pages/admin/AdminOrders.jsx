import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import toast from "react-hot-toast";

import { getAdminOrders, updateAdminOrderStatus } from "../../services/authService";

const statuses = ["ORDER_PLACED", "PAYMENT_PENDING", "PAYMENT_SUCCESS", "PROCESSING", "PACKED", "SHIPPED", "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED", "REFUND_REQUESTED", "REFUNDED"];

export default function AdminOrders() {
  const [orders, setOrders] = useState([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  async function refresh() {
    const { data } = await getAdminOrders();
    setOrders(data.data?.items || []);
  }

  useEffect(() => { refresh().catch(() => setOrders([])); }, []);

  const filtered = useMemo(() => orders.filter((order) => {
    const text = `${order.id} ${order.transaction_id} ${order.payment_method}`.toLowerCase();
    return (!search || text.includes(search.toLowerCase())) && (!status || order.order_status === status);
  }), [orders, search, status]);

  async function updateStatus(order, nextStatus) {
    await updateAdminOrderStatus(order.id, nextStatus);
    toast.success("Order status updated");
    await refresh();
  }

  return (
    <main className="pageStack">
      <section className="pageHero compactHero"><div><span className="eyebrowText">Order Management</span><h1>Marketplace order operations</h1><p>Search, filter, and update order status with payment context preserved.</p></div></section>
      <section className="panel toolbarPanel">
        <label className="searchInput"><Search size={18} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search orders or transactions" /></label>
        <select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All statuses</option>{statuses.map((item) => <option key={item} value={item}>{item}</option>)}</select>
      </section>
      <section className="adminTable panel">
        {filtered.map((order) => (
          <article key={order.id}>
            <div><strong>#{order.id.slice(-8)} • Rs. {order.total}</strong><span>{order.payment_method} • {order.payment_status} • {order.transaction_id || "No transaction"}</span></div>
            <span className="softBadge">{order.order_status}</span>
            <select value={order.order_status} onChange={(event) => updateStatus(order, event.target.value)}>{statuses.map((item) => <option key={item} value={item}>{item}</option>)}</select>
          </article>
        ))}
        {filtered.length === 0 && <div className="emptyState">No orders found.</div>}
      </section>
    </main>
  );
}
