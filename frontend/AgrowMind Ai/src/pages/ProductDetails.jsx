import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { BadgeCheck, ChevronLeft, Heart, MapPin, PackageCheck, ShieldCheck, ShoppingCart, Star, Truck } from "lucide-react";
import toast from "react-hot-toast";

import PublicNav from "../components/PublicNav";
import MobileBottomNavbar from "../components/MobileBottomNavbar";
import { PriceBlock, RatingBadge, StoreBadge, TrustStrip } from "../components/MarketplaceUI";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { getProduct } from "../services/authService";

const fallbackImage = "https://images.unsplash.com/photo-1464226184884-fa280b87c399?auto=format&fit=crop&w=1200&q=80";
const tabs = ["Description", "Specifications", "Reviews", "Q&A"];

export default function ProductDetails() {
  const { id } = useParams();
  const { add } = useCart();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [selectedImage, setSelectedImage] = useState("");
  const [activeTab, setActiveTab] = useState("Description");
  const [pinCode, setPinCode] = useState("");

  useEffect(() => {
    getProduct(id).then(({ data }) => {
      const nextProduct = data.product;
      setProduct(nextProduct);
      setSelectedImage(nextProduct.image || fallbackImage);
      const stored = JSON.parse(localStorage.getItem("agromind:recent-products") || "[]");
      const next = [nextProduct, ...stored.filter((item) => item.id !== nextProduct.id)].slice(0, 8);
      localStorage.setItem("agromind:recent-products", JSON.stringify(next));
    });
  }, [id]);

  const gallery = useMemo(() => {
    if (!product) return [];
    return [product.image || fallbackImage, ...(product.gallery || [])].filter(Boolean).slice(0, 7);
  }, [product]);

  async function addAndMaybeCheckout(goCheckout = false) {
    if (product.stock <= 0 || quantity > product.stock) {
      toast.error("Requested quantity is not available");
      return;
    }
    if (!isAuthenticated) {
      toast.error("Please login to buy products.");
      navigate("/login");
      return;
    }
    await add(product.id, quantity);
    toast.success("Added to cart");
    if (goCheckout) navigate("/checkout");
  }

  if (!product) {
    return (
      <main className="publicPage shopPage">
        <PublicNav />
        <div className="shopShell"><div className="productDetailSkeleton" /></div>
      </main>
    );
  }

  return (
    <main className="publicPage shopPage productDetailPage">
      <PublicNav />
      <div className="shopShell">
        <Link className="backToShop" to="/marketplace"><ChevronLeft size={17} /> Marketplace</Link>
        <section className="premiumProductDetail">
          <div className="productGallery">
            <motion.img alt={product.name} className="mainProductImage" key={selectedImage} src={selectedImage} initial={{ opacity: 0.4 }} animate={{ opacity: 1 }} />
            <div className="galleryRail">
              {gallery.map((item) => (
                <button className={selectedImage === item ? "active" : ""} key={item} onClick={() => setSelectedImage(item)} type="button">
                  <img alt={product.name} loading="lazy" src={item} />
                </button>
              ))}
            </div>
          </div>
          <article className="productBuyBox">
            <span className="productCategory">{product.category}</span>
            <h1>{product.name}</h1>
            <div className="detailRatingRow">
              <RatingBadge value={product.rating} />
              <span><Star size={15} /> 128 reviews</span>
              <StoreBadge seller={product.seller_name} />
            </div>
            <p>{product.short_description || product.description}</p>
            <PriceBlock price={product.price} mrp={product.mrp} />
            <div className="stockDeliveryRow">
              <span className={product.stock <= 0 ? "stockPill danger" : "stockPill"}>{product.stock <= 0 ? "Out of stock" : `${product.stock} available`}</span>
              <span><Truck size={16} /> Delivery in 2-5 days</span>
            </div>
            <div className="pinChecker">
              <MapPin size={18} />
              <input inputMode="numeric" maxLength="6" onChange={(event) => setPinCode(event.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="Enter delivery pincode" value={pinCode} />
              <button type="button">{pinCode.length === 6 ? "Available" : "Check"}</button>
            </div>
            <label className="quantityInput">
              <span>Quantity</span>
              <input max={Math.max(product.stock, 1)} min="1" onChange={(event) => setQuantity(Number(event.target.value))} type="number" value={quantity} />
            </label>
            <div className="detailTrustGrid">
              <span><ShieldCheck size={18} /> Secure payments</span>
              <span><PackageCheck size={18} /> Easy returns</span>
              <span><BadgeCheck size={18} /> Verified seller</span>
              <span><Heart size={18} /> Genuine products</span>
            </div>
            <div className="desktopCtas">
              <button className="secondaryButton" disabled={product.stock <= 0} onClick={() => addAndMaybeCheckout(false)} type="button"><ShoppingCart size={18} /> Add to Cart</button>
              <button className="primaryButton" disabled={product.stock <= 0} onClick={() => addAndMaybeCheckout(true)} type="button">Buy Now</button>
            </div>
          </article>
        </section>
        <TrustStrip />
        <section className="productTabs panel">
          <nav>
            {tabs.map((tab) => <button className={activeTab === tab ? "active" : ""} key={tab} onClick={() => setActiveTab(tab)} type="button">{tab}</button>)}
          </nav>
          {activeTab === "Description" && <p>{product.description || product.short_description || "Product information will be updated soon."}</p>}
          {activeTab === "Specifications" && <ul><li>Brand: {product.brand || "AgroMind verified"}</li><li>Pack: {product.unit_size || product.unit}</li><li>SKU: {product.sku || "AGM-FARM"}</li></ul>}
          {activeTab === "Reviews" && <p>Verified buyer reviews and photos will appear here after delivery.</p>}
          {activeTab === "Q&A" && <p>Ask crop usage, dosage, storage, and compatibility questions from the seller.</p>}
        </section>
      </div>
      <div className="stickyProductCta">
        <button disabled={product.stock <= 0} onClick={() => addAndMaybeCheckout(false)} type="button"><ShoppingCart size={18} /> Add</button>
        <button disabled={product.stock <= 0} onClick={() => addAndMaybeCheckout(true)} type="button">Buy Now</button>
      </div>
      <MobileBottomNavbar />
    </main>
  );
}
