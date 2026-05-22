import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Search, SlidersHorizontal } from "lucide-react";

import MarketplaceCarousel from "../components/MarketplaceCarousel";
import ProductCard from "../components/ProductCard";
import PublicNav from "../components/PublicNav";
import { useAuth } from "../context/AuthContext";
import { getProducts } from "../services/authService";

const categories = ["fertilizers", "seeds", "trees", "pesticides", "tools"];
const crops = ["tomato", "mango", "coconut"];

export default function Marketplace() {
  const { isAuthenticated } = useAuth();
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
      .then(({ data }) => !ignore && setProducts(data.items || []))
      .catch(() => !ignore && setProducts([]))
      .finally(() => !ignore && setLoading(false));
    return () => { ignore = true; };
  }, [query]);

  function updateFilter(key, value) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }

  return (
    <main className="publicPage">
      <PublicNav />
      <div className="pageStack">
      <section className="marketHero">
        <div>
          <span className="eyebrowText">AgroMind Marketplace</span>
          <h1>Farm inputs matched to crop intelligence.</h1>
          <p>Shop fertilizers, pesticides, seeds, saplings, and tools with AI-led recommendations.</p>
        </div>
        <Link className={isAuthenticated ? "primaryButton" : "secondaryButton"} to={isAuthenticated ? "/cart" : "/login"}>
          {isAuthenticated ? "Go to Cart" : "Login Required to Buy"}
        </Link>
      </section>
      <MarketplaceCarousel />
      <section className="marketFilters panel">
        <label className="searchInput"><Search size={18} /><input onChange={(event) => setSearch(event.target.value)} placeholder="Search products" value={search} /></label>
        <select onChange={(event) => updateFilter("category", event.target.value)} value={category}>
          <option value="">All categories</option>
          {categories.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
        <select onChange={(event) => updateFilter("crop", event.target.value)} value={crop}>
          <option value="">All crops</option>
          {crops.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
        {(disease || category || crop || search) && <button className="secondaryButton" onClick={() => { setSearch(""); setParams({}); }} type="button"><SlidersHorizontal size={17} /> Clear</button>}
      </section>
      {disease && <p className="recommendationNote">Showing products related to {disease.replaceAll("_", " ")}.</p>}
      <section className="productGrid">
        {loading && Array.from({ length: 8 }).map((_, index) => <div className="productSkeleton" key={index} />)}
        {!loading && products.map((product) => <ProductCard key={product.id} product={product} />)}
      </section>
      {!loading && products.length === 0 && <div className="emptyMarket">No products found.</div>}
      </div>
    </main>
  );
}
