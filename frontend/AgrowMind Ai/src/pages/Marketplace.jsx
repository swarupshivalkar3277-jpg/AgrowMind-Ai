import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { BadgeCheck, ChevronDown, Flame, Heart, LayoutDashboard, PackageCheck, Search, ShoppingCart, SlidersHorizontal, Truck, ShieldCheck } from "lucide-react";

import EmptyState from "../components/EmptyState";
import MobileBottomNavbar from "../components/MobileBottomNavbar";
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
} from "../components/MarketplaceUI";
import { useCart } from "../context/CartContext";
import { useVoiceInput } from "../hooks/useVoiceInput";
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
  const [visibleLimit, setVisibleLimit] = useState(24);
  const [categoryOpen, setCategoryOpen] = useState(false);
  const [recentlyViewed, setRecentlyViewed] = useState([]);
  const [filters, setFilters] = useState({ maxPrice: "", rating: "", brand: "", availability: "" });
  const category = params.get("category") || "";
  const crop = params.get("crop") || "";
  const disease = params.get("disease") || "";

  const debouncedSearch = useMemo(() => search.trim(), [search]);
  const voice = useVoiceInput({ onResult: setSearch });
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

  function selectCategory(value) {
    updateFilter("category", value);
    setCategoryOpen(false);
  }

  function updateDrawerFilter(key, value) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function clearFilters() {
    setFilters({ maxPrice: "", rating: "", brand: "", availability: "" });
    setSearch("");
    setParams(new URLSearchParams());
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

  const renderedProducts = visibleProducts.slice(0, visibleLimit);

  useEffect(() => {
    setVisibleLimit(24);
  }, [query, filters, sort]);

  return (
    <main className="publicPage shopPage">
      <PublicNav />
      <div className="shopShell">
        <MarketplaceHeader cartCount={cart.count} listening={voice.listening} onQueryChange={setSearch} onVoice={voice.start} query={search} />
        <div className="marketplaceLayout">
          <aside className="marketSidebar" aria-label="Marketplace filters and trust signals">
            <section className="sidebarBlock marketplaceQuickLinks">
              <strong>Quick links</strong>
              <Link to="/dashboard"><LayoutDashboard size={18} /> Dashboard</Link>
              <Link to="/orders"><PackageCheck size={18} /> Orders</Link>
              <Link to="/wishlist"><Heart size={18} /> Wishlist</Link>
              <Link to="/cart"><ShoppingCart size={18} /> Cart</Link>
            </section>
            <section className="sidebarBlock marketplaceTrust">
              <span><ShieldCheck size={17} /> Secure payments</span>
              <span><BadgeCheck size={17} /> Verified sellers</span>
              <span><Truck size={17} /> Order tracking</span>
              <span><PackageCheck size={17} /> Genuine products</span>
            </section>
            <section className="sidebarBlock">
              <button className="categoryDropButton" onClick={() => setCategoryOpen((current) => !current)} type="button">
                <span>Shop by category</span>
                <ChevronDown className={categoryOpen ? "open" : ""} size={19} />
              </button>
              <AnimatePresence initial={false}>
                {categoryOpen && (
                  <motion.div
                    animate={{ height: "auto", opacity: 1 }}
                    className="sidebarCategoryList"
                    exit={{ height: 0, opacity: 0 }}
                    initial={{ height: 0, opacity: 0 }}
                  >
                    <CategoryScroller active={category} onSelect={selectCategory} />
                  </motion.div>
                )}
              </AnimatePresence>
              <Link className="sidebarTextLink" to="/marketplace">View all categories</Link>
            </section>
            <section className="sidebarBlock">
              <label className="sidebarSelect">
                <span>Crop</span>
                <select onChange={(event) => updateFilter("crop", event.target.value)} value={crop}>
                  <option value="">All crops</option>
                  {crops.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
            </section>
            <section className="sidebarBlock marketplaceFilterPanel">
              <div className="sidebarBlockTitle">
                <strong><SlidersHorizontal size={17} /> Filters</strong>
                <button onClick={clearFilters} type="button">Clear</button>
              </div>
              <label className="sidebarSelect">
                <span>Max price</span>
                <input min="0" onChange={(event) => updateDrawerFilter("maxPrice", event.target.value)} placeholder="Example: 999" type="number" value={filters.maxPrice} />
              </label>
              <label className="sidebarSelect">
                <span>Minimum rating</span>
                <select onChange={(event) => updateDrawerFilter("rating", event.target.value)} value={filters.rating}>
                  <option value="">Any rating</option>
                  <option value="4">4 stars and above</option>
                  <option value="3">3 stars and above</option>
                </select>
              </label>
              <label className="sidebarSelect">
                <span>Brand</span>
                <select onChange={(event) => updateDrawerFilter("brand", event.target.value)} value={filters.brand}>
                  <option value="">All brands</option>
                  {brands.map((brand) => <option key={brand} value={brand}>{brand}</option>)}
                </select>
              </label>
              <label className="sidebarSelect">
                <span>Availability</span>
                <select onChange={(event) => updateDrawerFilter("availability", event.target.value)} value={filters.availability}>
                  <option value="">All products</option>
                  <option value="in_stock">In stock</option>
                  <option value="low_stock">Low stock</option>
                </select>
              </label>
            </section>
            <section className="sidebarBlock instantSearch">
              <Search size={18} />
              <div>
                <strong>Trending searches</strong>
                <div>{trending.map((item) => <button key={item} onClick={() => setSearch(item)} type="button">{item}</button>)}</div>
              </div>
            </section>
          </aside>
          <div className="marketMain">
            <BannerCarousel />
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
              {!loading && renderedProducts.map((product) => <ProductCard key={product.id} product={product} />)}
            </motion.div>
          </AnimatePresence>
          {!loading && visibleLimit < visibleProducts.length && <button className="secondaryButton loadMoreButton" onClick={() => setVisibleLimit((value) => value + 24)} type="button">Load more products</button>}
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
                  <img alt={product.name} loading="lazy" src={product.image} />
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
        </div>
      </div>
      <FilterDrawer brands={brands} filters={filters} onChange={updateDrawerFilter} onClose={() => setDrawerOpen(false)} open={drawerOpen} />
      <MobileBottomNavbar />
    </main>
  );
}
