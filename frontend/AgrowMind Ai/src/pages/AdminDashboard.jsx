import { useEffect, useState } from "react";

import StatsCard from "../components/StatsCard";
import { Boxes, PackageCheck, ShieldCheck, WalletCards } from "lucide-react";
import { createProduct, deleteProduct, getAdminOrders, getProducts, updateAdminOrderStatus } from "../services/authService";

const blankProduct = {
  name: "",
  category: "fertilizers",
  crop_type: [],
  disease_tags: [],
  price: 0,
  stock: 0,
  image: "",
  description: "",
  rating: 4,
};

export default function AdminDashboard() {
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [form, setForm] = useState(blankProduct);

  async function refresh() {
    const [productResult, orderResult] = await Promise.all([getProducts(), getAdminOrders()]);
    setProducts(productResult.data.items || []);
    setOrders(orderResult.data.items || []);
  }

  useEffect(() => {
    refresh().catch(() => {});
  }, []);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    await createProduct({
      ...form,
      crop_type: String(form.crop_type).split(",").map((item) => item.trim()).filter(Boolean),
      disease_tags: String(form.disease_tags).split(",").map((item) => item.trim()).filter(Boolean),
      price: Number(form.price),
      stock: Number(form.stock),
      rating: Number(form.rating),
    });
    setForm(blankProduct);
    await refresh();
  }

  const revenue = orders.reduce((sum, order) => sum + Number(order.total || 0), 0);

  return (
    <main className="pageStack">
      <section className="pageHero compactHero">
        <div>
          <span className="eyebrowText">Admin Dashboard</span>
          <h1>Platform control center</h1>
          <p>Manage users, sellers, products, orders, payments, and marketplace analytics from one protected route.</p>
        </div>
      </section>
      <section className="statsGrid">
        <StatsCard icon={ShieldCheck} label="Users" value="Role protected" />
        <StatsCard icon={Boxes} label="Products" value={products.length} tone="teal" />
        <StatsCard icon={PackageCheck} label="Orders" value={orders.length} tone="blue" />
        <StatsCard icon={WalletCards} label="Payments" value={`Rs. ${revenue}`} tone="emerald" />
      </section>
      <section className="adminGrid">
        <form className="panel checkoutForm" onSubmit={submit}>
          <h2>Product Management</h2>
          {["name", "category", "price", "stock", "image", "description", "rating"].map((field) => (
            <label key={field}>
              <span>{field}</span>
              <input onChange={(event) => update(field, event.target.value)} required={field !== "image"} value={form[field]} />
            </label>
          ))}
          <label><span>crop_type comma separated</span><input onChange={(event) => update("crop_type", event.target.value)} value={form.crop_type} /></label>
          <label><span>disease_tags comma separated</span><input onChange={(event) => update("disease_tags", event.target.value)} value={form.disease_tags} /></label>
          <button type="submit">Add Product</button>
        </form>
        <section className="panel">
          <div className="sectionHeader"><div><span className="eyebrowText">Inventory</span><h2>Products</h2></div></div>
          <div className="adminList">
            {products.map((product) => (
              <article key={product.id}>
                <span>{product.name}</span>
                <strong>Rs. {product.price}</strong>
                <span>{product.seller_name}</span>
                <button className="iconTextButton" onClick={() => deleteProduct(product.id).then(refresh)} type="button">Remove</button>
              </article>
            ))}
          </div>
        </section>
      </section>
      <section className="panel">
        <div className="sectionHeader"><div><span className="eyebrowText">Operations</span><h2>Order Management</h2></div></div>
        <div className="adminList">
          {orders.map((order) => (
            <article key={order.id}>
              <span>#{order.id.slice(-8)} - Rs. {order.total}</span>
              <strong>{order.payment_status}</strong>
              <span>{order.payment_method}</span>
              <select onChange={(event) => updateAdminOrderStatus(order.id, event.target.value).then(refresh)} value={order.order_status}>
                <option value="confirmed">confirmed</option>
                <option value="packed">packed</option>
                <option value="shipped">shipped</option>
                <option value="delivered">delivered</option>
                <option value="cancelled">cancelled</option>
              </select>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
