import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Flame, Search, ShieldCheck } from "lucide-react";

import EmptyState from "../components/EmptyState";
import ProductCard from "../components/ProductCard";
import PublicNav from "../components/PublicNav";
import {
  BannerCarousel,
  CategoryScroller,
  DealsTimer,
  FilterDrawer,
  ListingToolbar,
  MarketplaceHeader,
  SkeletonLoader,
  TrustStrip,
} from "../components/MarketplaceUI";
import { useCart } from "../context/CartContext";
import { getProducts } from "../services/authService";

const crops = ["tomato", "mango", "coconut"];
const trending = ["tomato blight spray", "mango flowering fertilizer", "coconut leaf rot", "neem oil", "drip irrigation"];
const brands = ["AgroMind", "GrowWell", "KisanCare", "GreenYield", "FarmPro"];

export default function Marketplace() {
  const { cart } = useCart();
  const [params, setParams] = useSearchParams();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState(params.get("search") || "");
  const [sort, setSort] = useState("featured");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [recentlyViewed, setRecentlyViewed] = useState([]);
  const [filters, setFilters] = useState({ maxPrice: "", rating: "", brand: "", availability: "" });
  const category = params.get("category") || "";
  const crop = params.get("crop") || "";
  const disease = params.get("disease") || "";

  const debouncedSearch = useMemo(() => search.trim(), [search]);
  const query = useMemo(() => ({ search: debouncedSearch, category, crop, disease }), [debouncedSearch, category, crop, disease]);

  useEffect(() => {
    const stored = JSON.parse(localStorage.getItem("agromind:recent-products") || "[]");
    setRecentlyViewed(stored.slice(0, 8));
  }, []);

  useEffect(() => {
    let ignore = false;
    const timeout = window.setTimeout(() => {
      setLoading(true);
      getProducts(query)
        .then(({ data }) => !ignore && setProducts(data.items || []))
        .catch(() => !ignore && setProducts([]))
        .finally(() => !ignore && setLoading(false));
    }, 260);
    return () => {
      ignore = true;
      window.clearTimeout(timeout);
    };
  }, [query]);

  function updateFilter(key, value) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }

  function updateDrawerFilter(key, value) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  const visibleProducts = useMemo(() => {
    let next = products.filter((product) => {
      if (filters.maxPrice && Number(product.price || 0) > Number(filters.maxPrice)) return false;
      if (filters.rating && Number(product.rating || 0) < Number(filters.rating)) return false;
      if (filters.brand && product.brand !== filters.brand) return false;
      if (filters.availability === "in_stock" && product.stock <= 0) return false;
      if (filters.availability === "low_stock" && !(product.stock > 0 && product.stock <= 5)) return false;
      return true;
    });
    if (sort === "price_low") next = [...next].sort((a, b) => Number(a.price || 0) - Number(b.price || 0));
    if (sort === "price_high") next = [...next].sort((a, b) => Number(b.price || 0) - Number(a.price || 0));
    if (sort === "rating") next = [...next].sort((a, b) => Number(b.rating || 0) - Number(a.rating || 0));
    return next;
  }, [filters, products, sort]);

  return (
    <main className="publicPage shopPage">
      <PublicNav />
      <div className="shopShell">
        <MarketplaceHeader cartCount={cart.count} onQueryChange={setSearch} query={search} />
        <BannerCarousel />
        <TrustStrip />
        <section className="shopSection">
          <div className="shopSectionHead">
            <div><span>Shop by category</span><h2>Everything your farm needs</h2></div>
            <Link to="/marketplace">View all</Link>
          </div>
          <CategoryScroller active={category} onSelect={(value) => updateFilter("category", value)} />
        </section>
        <section className="discoveryPanel">
          <div className="instantSearch">
            <Search size={18} />
            <div>
              <strong>Trending searches</strong>
              <div>{trending.map((item) => <button key={item} onClick={() => setSearch(item)} type="button">{item}</button>)}</div>
            </div>
          </div>
          <select onChange={(event) => updateFilter("crop", event.target.value)} value={crop}>
            <option value="">All crops</option>
            {crops.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </section>
        <section className="shopSection flashDeals">
          <div className="shopSectionHead">
            <div><span><Flame size={16} /> Flash deals</span><h2>Fast-moving farm inputs</h2></div>
            <DealsTimer />
          </div>
          <div className="dealRail">
            {(visibleProducts.length ? visibleProducts : products).slice(0, 6).map((product) => <ProductCard key={product.id} product={product} />)}
            {loading && <SkeletonLoader count={4} />}
          </div>
        </section>
        <section className="shopSection productListing">
          <div className="shopSectionHead">
            <div>
              <span>{disease ? `Matched to ${disease.replaceAll("_", " ")}` : "Recommended products"}</span>
              <h2>Marketplace picks for you</h2>
            </div>
            <ListingToolbar onFilter={() => setDrawerOpen(true)} onSort={setSort} sort={sort} />
          </div>
          <AnimatePresence mode="popLayout">
            <motion.div className="productGrid" layout>
              {loading && <SkeletonLoader count={8} />}
              {!loading && visibleProducts.map((product) => <ProductCard key={product.id} product={product} />)}
            </motion.div>
          </AnimatePresence>
          {!loading && visibleProducts.length === 0 && (
            <EmptyState
              icon={ShieldCheck}
              title="No matching farm inputs"
              text="Try a different crop, category, price range, or disease search."
            />
          )}
        </section>
        {recentlyViewed.length > 0 && (
          <section className="shopSection">
            <div className="shopSectionHead"><div><span>Recently viewed</span><h2>Continue comparing</h2></div></div>
            <div className="recentRail">
              {recentlyViewed.map((product) => (
                <Link className="miniProduct" key={product.id} to={`/marketplace/product/${product.id}`}>
                  <img alt={product.name} src={product.image} />
                  <span>{product.category}</span>
                  <strong>{product.name}</strong>
                  <small>Rs. {product.price}</small>
                </Link>
              ))}
            </div>
          </section>
        )}
        <section className="shopSection brandShowcase">
          {brands.map((brand) => <span key={brand}>{brand}</span>)}
        </section>
      </div>
      <FilterDrawer brands={brands} filters={filters} onChange={updateDrawerFilter} onClose={() => setDrawerOpen(false)} open={drawerOpen} />
    </main>
  );
}
