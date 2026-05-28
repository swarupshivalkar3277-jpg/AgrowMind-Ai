import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  BadgeCheck,
  Bell,
  ChevronRight,
  Clock3,
  Filter,
  Heart,
  Leaf,
  Mic,
  PackageCheck,
  Search,
  ShieldCheck,
  ShoppingCart,
  SlidersHorizontal,
  Sparkles,
  Star,
  Store,
  Truck,
  UserRound,
  X,
} from "lucide-react";
import { Link } from "react-router-dom";

export const categories = [
  { key: "seeds", label: "Seeds", icon: Leaf },
  { key: "fertilizers", label: "Fertilizers", icon: Sparkles },
  { key: "pesticides", label: "Crop Care", icon: ShieldCheck },
  { key: "tools", label: "Tools", icon: SlidersHorizontal },
  { key: "irrigation", label: "Irrigation", icon: Truck },
  { key: "machinery", label: "Machinery", icon: PackageCheck },
  { key: "animal-care", label: "Animal Care", icon: Heart },
];

const banners = [
  {
    title: "Monsoon-ready crop protection",
    text: "Fungicides, sprayers, and AI-matched treatment kits for tomato, mango, and coconut farms.",
    cta: "Shop Crop Care",
    category: "pesticides",
    image: "https://images.unsplash.com/photo-1625246333195-78d9c38ad449?auto=format&fit=crop&w=1600&q=80",
  },
  {
    title: "Certified seeds and saplings",
    text: "High-quality planting inputs with verified sellers and fast order tracking.",
    cta: "Explore Seeds",
    category: "seeds",
    image: "https://images.unsplash.com/photo-1523348837708-15d4a09cfac2?auto=format&fit=crop&w=1600&q=80",
  },
  {
    title: "Smart nutrition for better yield",
    text: "Fertilizers, micronutrients, and soil conditioners curated for local crop needs.",
    cta: "View Fertilizers",
    category: "fertilizers",
    image: "https://images.unsplash.com/photo-1463123081488-789f998ac9c4?auto=format&fit=crop&w=1600&q=80",
  },
];

export function MarketplaceHeader({ cartCount = 0, listening = false, onVoice, query, onQueryChange }) {
  const [focused, setFocused] = useState(false);
  return (
    <header className="shopHeader">
      <Link className="shopBrand" to="/marketplace" aria-label="AgroMind Marketplace">
        <span>Ag</span>
        <strong>AgroMind</strong>
      </Link>
      <label className={`shopSearch ${focused ? "focused" : ""}`}>
        <Search size={18} />
        <input
          aria-label="Search marketplace"
          onBlur={() => setFocused(false)}
          onChange={(event) => onQueryChange?.(event.target.value)}
          onFocus={() => setFocused(true)}
          placeholder="Search seeds, fertilizers, tools"
          value={query || ""}
        />
        <button aria-label="Voice search" className={listening ? "listening" : ""} onClick={onVoice} type="button"><Mic size={18} /></button>
      </label>
      <nav className="shopHeaderActions" aria-label="Marketplace shortcuts">
        <Link className="shopHeaderTextLink" to="/dashboard">Dashboard</Link>
        <Link className="shopHeaderTextLink" to="/orders">Orders</Link>
        <button aria-label="Notifications" type="button"><Bell size={19} /></button>
        <Link aria-label="Cart" className="shopCartLink" to="/cart"><ShoppingCart size={19} />{cartCount > 0 && <span>{cartCount}</span>}</Link>
        <Link aria-label="Profile" to="/dashboard"><UserRound size={19} /></Link>
      </nav>
    </header>
  );
}

export function BannerCarousel() {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setIndex((current) => (current + 1) % banners.length), 4500);
    return () => window.clearInterval(timer);
  }, []);
  const banner = banners[index];
  return (
    <section className="bannerCarousel" aria-label="Marketplace promotions">
      <AnimatePresence mode="wait">
        <motion.article
          animate={{ opacity: 1, x: 0 }}
          className="bannerSlide"
          exit={{ opacity: 0, x: -18 }}
          initial={{ opacity: 0, x: 18 }}
          key={banner.title}
          style={{ backgroundImage: `linear-gradient(90deg, rgba(20,83,45,.92), rgba(22,101,52,.72), rgba(15,23,42,.12)), url(${banner.image})` }}
          transition={{ duration: 0.38 }}
        >
          <div>
            <span>AgroMind Deals</span>
            <h1>{banner.title}</h1>
            <p>{banner.text}</p>
            <Link className="bannerCta" to={`/marketplace?category=${banner.category}`}>{banner.cta}<ChevronRight size={17} /></Link>
          </div>
        </motion.article>
      </AnimatePresence>
      <div className="bannerDots">
        {banners.map((item, itemIndex) => (
          <button aria-label={`Show banner ${itemIndex + 1}`} className={itemIndex === index ? "active" : ""} key={item.title} onClick={() => setIndex(itemIndex)} type="button" />
        ))}
      </div>
    </section>
  );
}

export function CategoryScroller({ active, onSelect }) {
  return (
    <section className="categoryScroller" aria-label="Shop by category">
      {categories.map(({ key, label, icon: Icon }) => (
        <button className={active === key ? "active" : ""} key={key} onClick={() => onSelect?.(key)} type="button">
          <span><Icon size={22} /></span>
          <strong>{label}</strong>
        </button>
      ))}
    </section>
  );
}

export function RatingBadge({ value = 4 }) {
  return <span className="ratingBadge"><Star size={13} fill="currentColor" /> {Number(value || 0).toFixed(1)}</span>;
}

export function PriceBlock({ price = 0, mrp = 0 }) {
  const discount = mrp > price ? Math.round(((mrp - price) / mrp) * 100) : 0;
  return (
    <div className="priceBlock">
      <strong>Rs. {price}</strong>
      {mrp > price && <del>Rs. {mrp}</del>}
      {discount > 0 && <span>{discount}% off</span>}
    </div>
  );
}

export function FilterDrawer({ open, filters, onChange, onClose, brands = [] }) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button aria-label="Close filters" className="drawerScrim" onClick={onClose} type="button" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
          <motion.aside className="filterDrawer" initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }} transition={{ type: "spring", damping: 26, stiffness: 260 }}>
            <div className="drawerHead"><strong>Filters</strong><button aria-label="Close filters" onClick={onClose} type="button"><X size={19} /></button></div>
            <label><span>Max price</span><input min="0" onChange={(event) => onChange("maxPrice", event.target.value)} type="number" value={filters.maxPrice} /></label>
            <label><span>Minimum rating</span><select onChange={(event) => onChange("rating", event.target.value)} value={filters.rating}><option value="">Any rating</option><option value="4">4 stars and above</option><option value="3">3 stars and above</option></select></label>
            <label><span>Brand</span><select onChange={(event) => onChange("brand", event.target.value)} value={filters.brand}><option value="">All brands</option>{brands.map((brand) => <option key={brand} value={brand}>{brand}</option>)}</select></label>
            <label><span>Availability</span><select onChange={(event) => onChange("availability", event.target.value)} value={filters.availability}><option value="">All</option><option value="in_stock">In stock</option><option value="low_stock">Low stock</option></select></label>
            <button className="primaryButton" onClick={onClose} type="button">Apply Filters</button>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

export function SkeletonLoader({ count = 8 }) {
  return Array.from({ length: count }).map((_, index) => <div className="shopSkeleton" key={index} />);
}

export function TrustStrip() {
  return (
    <section className="trustStrip">
      <span><ShieldCheck size={18} /> Secure payments</span>
      <span><BadgeCheck size={18} /> Verified sellers</span>
      <span><Truck size={18} /> Order tracking</span>
      <span><PackageCheck size={18} /> Genuine inputs</span>
    </section>
  );
}

export function DealsTimer() {
  const [seconds, setSeconds] = useState(4 * 3600 + 18 * 60);
  useEffect(() => {
    const timer = window.setInterval(() => setSeconds((current) => Math.max(0, current - 1)), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const time = useMemo(() => {
    const hours = String(Math.floor(seconds / 3600)).padStart(2, "0");
    const minutes = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
    const secs = String(seconds % 60).padStart(2, "0");
    return `${hours}:${minutes}:${secs}`;
  }, [seconds]);
  return <span className="dealsTimer"><Clock3 size={16} /> Ends in {time}</span>;
}

export function ListingToolbar({ sort, onSort, onFilter }) {
  return (
    <div className="listingToolbar">
      <button className="secondaryButton" onClick={onFilter} type="button"><Filter size={17} /> Filter</button>
      <select aria-label="Sort products" onChange={(event) => onSort(event.target.value)} value={sort}>
        <option value="featured">Featured</option>
        <option value="rating">Top rated</option>
        <option value="price_low">Price low to high</option>
        <option value="price_high">Price high to low</option>
      </select>
    </div>
  );
}

export function StoreBadge({ seller = "AgroMind Store" }) {
  return <span className="storeBadge"><Store size={15} /> {seller}</span>;
}
