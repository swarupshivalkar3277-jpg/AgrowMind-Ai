import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Edit3, Plus, Search, Trash2 } from "lucide-react";
import toast from "react-hot-toast";

import { deleteAdminProduct, getProducts } from "../../services/authService";

export default function AdminProducts() {
  const [products, setProducts] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);

  async function refresh() {
    const { data } = await getProducts();
    setProducts(data.items || data.data?.items || []);
  }

  useEffect(() => {
    refresh().catch(() => setProducts([])).finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => products.filter((product) => `${product.name} ${product.category} ${product.sku}`.toLowerCase().includes(query.toLowerCase())), [products, query]);

  async function remove(productId) {
    await deleteAdminProduct(productId);
    toast.success("Product deleted");
    await refresh();
  }

  return (
    <main className="pageStack">
      <section className="pageHero compactHero">
        <div>
          <span className="eyebrowText">Product Management</span>
          <h1>Inventory and catalog operations</h1>
          <p>Add, edit, delete, update stock, and review marketplace-ready product cards.</p>
        </div>
        <Link className="primaryButton" to="/admin/products/add"><Plus size={17} /> Add Product</Link>
      </section>

      <section className="panel toolbarPanel">
        <label className="searchInput"><Search size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search products, SKU, category" /></label>
      </section>

      <section className="adminProductGrid">
        {loading && Array.from({ length: 6 }).map((_, index) => <div className="productSkeleton" key={index} />)}
        {!loading && filtered.map((product) => (
          <article className="productCard adminProductCard" key={product.id}>
            <img alt={product.name} src={product.image || "https://images.unsplash.com/photo-1464226184884-fa280b87c399?auto=format&fit=crop&w=900&q=80"} />
            <div className="productCardBody">
              <div>
                <span className="productCategory">{product.category}</span>
                <h3>{product.name}</h3>
                <p>{product.short_description || product.description}</p>
              </div>
              <div className="productMeta"><strong>Rs. {product.price}</strong><span>{product.rating}/5</span><span>Stock {product.stock}</span></div>
              {product.stock <= 0 && <span className="alert">Out of Stock</span>}
              <div className="productActions">
                <Link className="iconTextButton" to={`/admin/products/edit/${product.id}`}><Edit3 size={16} /> Edit</Link>
                <button className="iconTextButton dangerText" onClick={() => remove(product.id)} type="button"><Trash2 size={16} /> Delete</button>
              </div>
            </div>
          </article>
        ))}
      </section>
      {!loading && filtered.length === 0 && <div className="emptyMarket">No products found.</div>}
    </main>
  );
}
