import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import ProductCard from "../components/ProductCard";
import { getProducts } from "../services/authService";

const categories = ["fertilizers", "pesticides", "seeds", "trees", "organic"];
const crops = ["tomato", "mango", "coconut"];

export default function Marketplace() {
  const [params, setParams] = useSearchParams();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState(params.get("search") || "");
  const category = params.get("category") || "";
  const crop = params.get("crop") || "";
  const disease = params.get("disease") || "";

  const query = useMemo(() => ({ search, category, crop, disease }), [search, category, crop, disease]);

  useEffect(() => {
    let ignore = false;
    setLoading(true);
    getProducts(query)
      .then(({ data }) => {
        if (!ignore) {
          setProducts(data.items || []);
        }
      })
      .catch(() => {
        if (!ignore) {
          setProducts([]);
        }
      })
      .finally(() => {
        if (!ignore) {
          setLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [query]);

  function updateFilter(key, value) {
    const next = new URLSearchParams(params);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setParams(next);
  }

  return (
    <main className="marketPage">
      <section className="marketHero">
        <div>
          <p className="eyebrow">AgroMind Marketplace</p>
          <h1>Inputs, saplings, and treatments matched to crop health.</h1>
          <p>Shop fertilizers, pesticides, seeds, trees, and organic solutions connected to AI predictions.</p>
        </div>
        <Link className="primaryButton" to="/cart">Go to Cart</Link>
      </section>

      <section className="marketFilters panel">
        <input onChange={(event) => setSearch(event.target.value)} placeholder="Search products" value={search} />
        <select onChange={(event) => updateFilter("category", event.target.value)} value={category}>
          <option value="">All categories</option>
          {categories.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
        <select onChange={(event) => updateFilter("crop", event.target.value)} value={crop}>
          <option value="">All crops</option>
          {crops.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
        {(disease || category || crop || search) && (
          <button className="secondaryButton" onClick={() => { setSearch(""); setParams({}); }} type="button">Clear</button>
        )}
      </section>

      {disease && <p className="recommendationNote">Showing products related to {disease.replaceAll("_", " ")}.</p>}

      <section className="productGrid">
        {loading && Array.from({ length: 6 }).map((_, index) => <div className="productSkeleton" key={index} />)}
        {!loading && products.map((product) => <ProductCard key={product.id} product={product} />)}
      </section>
      {!loading && products.length === 0 && <div className="panel emptyMarket">No products found.</div>}
    </main>
  );
}
