import { useEffect, useState } from "react";

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
  const [message, setMessage] = useState("");

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
    setMessage("");
    await createProduct({
      ...form,
      crop_type: form.crop_type.split(",").map((item) => item.trim()).filter(Boolean),
      disease_tags: form.disease_tags.split(",").map((item) => item.trim()).filter(Boolean),
      price: Number(form.price),
      stock: Number(form.stock),
      rating: Number(form.rating),
    });
    setForm(blankProduct);
    setMessage("Product submitted to the marketplace.");
    await refresh();
  }

  return (
    <main className="marketPage">
      <section className="marketHero sellerHero">
        <div>
          <p className="eyebrow">Seller Center</p>
          <h1>List farm inputs for AgroMind buyers.</h1>
          <p>Farmers, sellers, and admins can add fertilizers, pesticides, seeds, saplings, and organic products.</p>
        </div>
      </section>

      <section className="adminGrid">
        <form className="panel checkoutForm" onSubmit={submit}>
          <h2>Add Product for Selling</h2>
          <label>
            <span>Name</span>
            <input onChange={(event) => update("name", event.target.value)} required value={form.name} />
          </label>
          <label>
            <span>Category</span>
            <select onChange={(event) => update("category", event.target.value)} value={form.category}>
              <option value="fertilizers">Fertilizers</option>
              <option value="pesticides">Pesticides</option>
              <option value="seeds">Seeds</option>
              <option value="trees">Trees/Saplings</option>
              <option value="organic">Organic Products</option>
            </select>
          </label>
          <label>
            <span>Crop types, comma separated</span>
            <input onChange={(event) => update("crop_type", event.target.value)} placeholder="tomato, mango" value={form.crop_type} />
          </label>
          <label>
            <span>Disease tags, comma separated</span>
            <input onChange={(event) => update("disease_tags", event.target.value)} placeholder="early_blight, healthy" value={form.disease_tags} />
          </label>
          <label>
            <span>Price</span>
            <input min="0" onChange={(event) => update("price", event.target.value)} required type="number" value={form.price} />
          </label>
          <label>
            <span>Stock</span>
            <input min="0" onChange={(event) => update("stock", event.target.value)} required type="number" value={form.stock} />
          </label>
          <label>
            <span>Image URL</span>
            <input onChange={(event) => update("image", event.target.value)} placeholder="https://..." value={form.image} />
          </label>
          <label>
            <span>Description</span>
            <input onChange={(event) => update("description", event.target.value)} required value={form.description} />
          </label>
          <label>
            <span>Rating</span>
            <input max="5" min="0" onChange={(event) => update("rating", event.target.value)} step="0.1" type="number" value={form.rating} />
          </label>
          {message && <div className="successAlert">{message}</div>}
          <button type="submit">Add Product</button>
        </form>

        <section className="panel">
          <div className="sectionHeader">
            <h2>Your Products</h2>
            <span>{products.length} listed</span>
          </div>
          <div className="adminList">
            {products.map((product) => (
              <article key={product.id}>
                <span>{product.name}</span>
                <strong>Rs. {product.price}</strong>
                <button className="iconTextButton" onClick={() => deleteProduct(product.id).then(refresh)} type="button">Delete</button>
              </article>
            ))}
            {products.length === 0 && <p>No products listed yet.</p>}
          </div>
        </section>
      </section>
    </main>
  );
}
