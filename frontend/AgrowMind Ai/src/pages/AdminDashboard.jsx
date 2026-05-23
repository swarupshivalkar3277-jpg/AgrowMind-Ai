import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { BarChart3, Boxes, PackageCheck, Search, ShieldCheck, Users, WalletCards } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import StatsCard from "../components/StatsCard";
import {
  blockAdminUser,
  createAdminProduct,
  deleteAdminProduct,
  deleteAdminUser,
  getAdminAnalytics,
  getAdminOrders,
  getAdminUsers,
  getProducts,
  updateAdminOrderStatus,
  updateAdminProduct,
} from "../services/authService";
import { useAuth } from "../context/AuthContext";

const blankProduct = {
  name: "",
  category: "fertilizers",
  crop_type: "",
  disease_tags: "",
  price: 0,
  stock: 0,
  image: "",
  description: "",
  rating: 4,
};

const statuses = ["pending", "paid", "processing", "shipped", "delivered", "cancelled"];

function normalizeProduct(form) {
  return {
    ...form,
    crop_type: String(form.crop_type).split(",").map((item) => item.trim()).filter(Boolean),
    disease_tags: String(form.disease_tags).split(",").map((item) => item.trim()).filter(Boolean),
    price: Number(form.price),
    stock: Number(form.stock),
    rating: Number(form.rating),
  };
}

export default function AdminDashboard() {
  const { user } = useAuth();
  const [analytics, setAnalytics] = useState(null);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState(blankProduct);
  const [editingId, setEditingId] = useState("");
  const [userSearch, setUserSearch] = useState("");
  const [orderStatus, setOrderStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function refresh() {
    setError("");
    const [analyticsResult, productResult, orderResult, userResult] = await Promise.all([
      getAdminAnalytics(),
      getProducts(),
      getAdminOrders(),
      getAdminUsers({ search: userSearch }),
    ]);
    setAnalytics(analyticsResult.data.data || {});
    setProducts(productResult.data.items || productResult.data.data?.items || []);
    setOrders(orderResult.data.data?.items || []);
    setUsers(userResult.data.data?.items || []);
  }

  useEffect(() => {
    setLoading(true);
    refresh()
      .catch((err) => setError(err?.response?.data?.error || err?.message || "Admin data failed to load"))
      .finally(() => setLoading(false));
  }, []);

  async function searchUsers(event) {
    event.preventDefault();
    await refresh();
  }

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function startEdit(product) {
    setEditingId(product.id);
    setForm({
      name: product.name || "",
      category: product.category || "fertilizers",
      crop_type: (product.crop_type || []).join(", "),
      disease_tags: (product.disease_tags || []).join(", "),
      price: product.price || 0,
      stock: product.stock || 0,
      image: product.image || "",
      description: product.description || "",
      rating: product.rating || 4,
    });
  }

  async function submitProduct(event) {
    event.preventDefault();
    const payload = normalizeProduct(form);
    if (editingId) {
      await updateAdminProduct(editingId, payload);
      toast.success("Product updated");
    } else {
      await createAdminProduct(payload);
      toast.success("Product added");
    }
    setEditingId("");
    setForm(blankProduct);
    await refresh();
  }

  async function removeProduct(productId) {
    await deleteAdminProduct(productId);
    toast.success("Product deleted");
    await refresh();
  }

  async function removeUser(userId) {
    await deleteAdminUser(userId);
    toast.success("User deleted");
    await refresh();
  }

  async function toggleBlock(targetUser) {
    await blockAdminUser(targetUser.id, !targetUser.blocked);
    toast.success(targetUser.blocked ? "User unblocked" : "User blocked");
    await refresh();
  }

  const filteredOrders = useMemo(
    () => (orderStatus ? orders.filter((order) => order.order_status === orderStatus) : orders),
    [orders, orderStatus]
  );

  if (loading) {
    return <main className="stateScreen"><span className="spinner" /><h1>Loading admin dashboard</h1></main>;
  }

  return (
    <main className="pageStack">
      <section className="pageHero compactHero">
        <div>
          <span className="eyebrowText">Admin Dashboard</span>
          <h1>Platform control center</h1>
          <p>Manage products, users, payments, orders, and AI analytics from one protected workspace.</p>
        </div>
      </section>

      {error && <div className="alert">{error}</div>}

      <section className="statsGrid">
        <StatsCard icon={Users} label="Total users" value={analytics?.total_users ?? 0} />
        <StatsCard icon={ShieldCheck} label="Farmers" value={analytics?.total_farmers ?? 0} tone="teal" />
        <StatsCard icon={PackageCheck} label="Orders" value={analytics?.total_orders ?? 0} tone="blue" />
        <StatsCard icon={WalletCards} label="Revenue" value={`Rs. ${analytics?.total_revenue ?? 0}`} tone="emerald" />
        <StatsCard icon={Boxes} label="Low stock" value={analytics?.low_stock_products ?? 0} tone="amber" />
        <StatsCard icon={BarChart3} label="AI predictions" value={analytics?.total_ai_predictions ?? 0} tone="violet" />
      </section>

      <section className="adminGrid">
        <form className="panel checkoutForm" onSubmit={submitProduct}>
          <h2>{editingId ? "Edit Product" : "Add Product"}</h2>
          {["name", "category", "price", "stock", "image", "description", "rating"].map((field) => (
            <label key={field}>
              <span>{field}</span>
              <input onChange={(event) => update(field, event.target.value)} required={field !== "image"} value={form[field]} />
            </label>
          ))}
          <label><span>crop_type comma separated</span><input onChange={(event) => update("crop_type", event.target.value)} value={form.crop_type} /></label>
          <label><span>disease_tags comma separated</span><input onChange={(event) => update("disease_tags", event.target.value)} value={form.disease_tags} /></label>
          <button type="submit">{editingId ? "Save Product" : "Add Product"}</button>
          {editingId && <button className="secondaryButton" onClick={() => { setEditingId(""); setForm(blankProduct); }} type="button">Cancel Edit</button>}
        </form>

        <section className="panel">
          <div className="sectionHeader"><div><span className="eyebrowText">AI Analytics</span><h2>Detected diseases</h2></div></div>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={analytics?.top_diseases || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#2563eb" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </section>

      <section className="panel">
        <div className="sectionHeader"><div><span className="eyebrowText">Inventory</span><h2>Products</h2></div></div>
        <div className="adminList">
          {products.length === 0 && <p className="mutedText">No products yet.</p>}
          {products.map((product) => (
            <article key={product.id}>
              <span>{product.name}</span>
              <strong>Rs. {product.price}</strong>
              <span>Stock {product.stock}</span>
              <button className="iconTextButton" onClick={() => startEdit(product)} type="button">Edit</button>
              <button className="iconTextButton" onClick={() => removeProduct(product.id)} type="button">Delete</button>
            </article>
          ))}
        </div>
      </section>

      <section className="adminGrid">
        <section className="panel">
          <div className="sectionHeader">
            <div><span className="eyebrowText">Users</span><h2>User Management</h2></div>
            <form className="inlineSearch" onSubmit={searchUsers}>
              <Search size={16} />
              <input onChange={(event) => setUserSearch(event.target.value)} placeholder="Search users" value={userSearch} />
            </form>
          </div>
          <div className="adminList">
            {users.map((targetUser) => (
              <article key={targetUser.id}>
                <span>{targetUser.name}</span>
                <strong>{targetUser.role}</strong>
                <span>{targetUser.email}</span>
                <button className="iconTextButton" disabled={targetUser.id === user?.id} onClick={() => toggleBlock(targetUser)} type="button">
                  {targetUser.blocked ? "Unblock" : "Block"}
                </button>
                <button className="iconTextButton" disabled={targetUser.id === user?.id} onClick={() => removeUser(targetUser.id)} type="button">Delete</button>
              </article>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="sectionHeader">
            <div><span className="eyebrowText">Orders</span><h2>Order Management</h2></div>
            <select onChange={(event) => setOrderStatus(event.target.value)} value={orderStatus}>
              <option value="">All statuses</option>
              {statuses.map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
          </div>
          <div className="adminList">
            {filteredOrders.map((order) => (
              <article key={order.id}>
                <span>#{order.id.slice(-8)} - Rs. {order.total}</span>
                <strong>{order.payment_status}</strong>
                <span>{order.payment_method}</span>
                <select onChange={(event) => updateAdminOrderStatus(order.id, event.target.value).then(refresh)} value={order.order_status}>
                  {statuses.map((status) => <option key={status} value={status}>{status}</option>)}
                </select>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}
