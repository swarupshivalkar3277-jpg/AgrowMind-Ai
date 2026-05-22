import { useEffect, useState } from "react";
import toast from "react-hot-toast";

import StatsCard from "../components/StatsCard";
import { Boxes, PackageCheck, TrendingUp, WalletCards } from "lucide-react";
import { createProduct, deleteProduct, getSellerProducts } from "../services/authService";

const blankProduct = {
  name: "",
  category: "fertilizers",
  crop_type: "",
  disease_tags: "",
  price: "",
  stock: "",
  image: "",
  description: "",
  rating: "4.5",
};

export default function SellerDashboard() {
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState(blankProduct);

  async function refresh() {
    const { data } = await getSellerProducts();
    setProducts(data.items || []);
  }

  useEffect(() => {
    refresh().catch(() => setProducts([]));
  }, []);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    await createProduct({
      ...form,
      crop_type: form.crop_type.split(",").map((item) => item.trim()).filter(Boolean),
      disease_tags: form.disease_tags.split(",").map((item) => item.trim()).filter(Boolean),
      price: Number(form.price),
      stock: Number(form.stock),
      rating: Number(form.rating),
    });
    setForm(blankProduct);
    toast.success("Product submitted to the marketplace");
    await refresh();
  }

  return (
    <main className="pageStack">
      <section className="pageHero compactHero">
        <div>
          <span className="eyebrowText">Seller Center</span>
          <h1>List and manage farm inputs</h1>
          <p>Add fertilizers, pesticides, seeds, saplings, tools, inventory, shipping details, and crop tags.</p>
        </div>
      </section>
      <section className="statsGrid">
        <StatsCard icon={Boxes} label="Products" value={products.length} />
        <StatsCard icon={PackageCheck} label="Inventory Units" value={products.reduce((sum, item) => sum + Number(item.stock || 0), 0)} tone="teal" />
        <StatsCard icon={TrendingUp} label="Sales" value="Live" tone="blue" />
        <StatsCard icon={WalletCards} label="Payouts" value="Ready" tone="emerald" />
      </section>
      <section className="adminGrid">
        <form className="panel checkoutForm" onSubmit={submit}>
          <h2>Add Product</h2>
          <label><span>Title</span><input onChange={(event) => update("name", event.target.value)} required value={form.name} /></label>
          <label>
            <span>Category</span>
            <select onChange={(event) => update("category", event.target.value)} value={form.category}>
              <option value="fertilizers">Fertilizers</option>
              <option value="pesticides">Pesticides</option>
              <option value="seeds">Seeds</option>
              <option value="trees">Trees/Saplings</option>
              <option value="tools">Farming Tools</option>
            </select>
          </label>
          <label><span>Crop types</span><input onChange={(event) => update("crop_type", event.target.value)} placeholder="tomato, mango" value={form.crop_type} /></label>
          <label><span>Disease tags</span><input onChange={(event) => update("disease_tags", event.target.value)} placeholder="early_blight, healthy" value={form.disease_tags} /></label>
          <label><span>Price</span><input min="0" onChange={(event) => update("price", event.target.value)} required type="number" value={form.price} /></label>
          <label><span>Stock</span><input min="0" onChange={(event) => update("stock", event.target.value)} required type="number" value={form.stock} /></label>
          <label><span>Product image URL</span><input onChange={(event) => update("image", event.target.value)} placeholder="https://..." value={form.image} /></label>
          <label><span>Shipping details</span><input placeholder="Ships in 2-4 days, packed safely" /></label>
          <label><span>Description</span><textarea onChange={(event) => update("description", event.target.value)} required value={form.description} /></label>
          <button type="submit">Publish Product</button>
        </form>
        <section className="panel">
          <div className="sectionHeader">
            <div><span className="eyebrowText">Inventory</span><h2>Your Products</h2></div>
            <span>{products.length} listed</span>
          </div>
          <div className="adminList">
            {products.map((product) => (
              <article key={product.id}>
                <span>{product.name}</span>
                <strong>Rs. {product.price}</strong>
                <span>{product.stock} in stock</span>
                <button className="iconTextButton" onClick={() => deleteProduct(product.id).then(refresh)} type="button">Remove</button>
              </article>
            ))}
            {products.length === 0 && <p>No products listed yet.</p>}
          </div>
        </section>
      </section>
    </main>
  );
}
