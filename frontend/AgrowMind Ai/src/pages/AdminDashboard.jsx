import { useEffect, useState } from "react";

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

  return (
    <main className="marketPage">
      <section className="adminGrid">
        <form className="panel checkoutForm" onSubmit={submit}>
          <h1>Admin Products</h1>
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
          <h2>Inventory</h2>
          <div className="adminList">
            {products.map((product) => (
              <article key={product.id}>
                <span>{product.name}</span>
                <strong>₹{product.price}</strong>
                <button className="iconTextButton" onClick={() => deleteProduct(product.id).then(refresh)} type="button">Delete</button>
              </article>
            ))}
          </div>
        </section>
      </section>
      <section className="panel">
        <h2>Manage Orders</h2>
        <div className="adminList">
          {orders.map((order) => (
            <article key={order.id}>
              <span>#{order.id.slice(-8)} - ₹{order.total} - {order.order_status}</span>
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
