import { Link, useNavigate } from "react-router-dom";
import { Heart, ShoppingCart, Truck } from "lucide-react";
import { motion } from "framer-motion";
import toast from "react-hot-toast";

import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { toggleWishlist } from "../services/authService";
import { PriceBlock, RatingBadge } from "./MarketplaceUI";

export default function ProductCard({ product }) {
  const { add } = useCart();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  async function handleAdd() {
    if (product.stock <= 0) {
      toast.error("This product is out of stock");
      return;
    }
    if (!isAuthenticated) {
      toast.error("Login required to buy products");
      navigate("/login");
      return;
    }
    await add(product.id, 1);
    toast.success("Added to cart");
  }

  async function handleWishlist() {
    if (!isAuthenticated) {
      toast.error("Login required to save products");
      navigate("/login");
      return;
    }
    await toggleWishlist(product.id);
    toast.success("Wishlist updated");
  }

  const discount = product.mrp > product.price ? Math.round(((product.mrp - product.price) / product.mrp) * 100) : 0;

  return (
    <motion.article className="productCard shopProductCard" whileHover={{ y: -4 }} transition={{ duration: 0.18 }}>
      <Link className="productImageLink" to={`/marketplace/product/${product.id}`}>
        <div className="productBadgeStack">
          {discount > 0 && <span>{discount}% OFF</span>}
          {Number(product.rating || 0) >= 4.5 && <span>Bestseller</span>}
          {product.stock > 0 && product.stock <= 5 && <span>Low stock</span>}
        </div>
        <img alt={product.name} loading="lazy" src={product.image || "https://images.unsplash.com/photo-1464226184884-fa280b87c399?auto=format&fit=crop&w=900&q=80"} />
      </Link>
      <div className="productCardBody">
        <div>
          <span className="productCategory">{product.category}</span>
          <h3>{product.name}</h3>
          <p>{product.description}</p>
          <small className="mutedText">{product.unit_size || product.unit || "1 piece"}</small>
          {product.stock <= 0 ? <span className="alert">Out of Stock</span> : <span className="deliveryPill"><Truck size={14} /> Delivery in 2-5 days</span>}
        </div>
        <div className="productMeta">
          <PriceBlock price={product.price} mrp={product.mrp} />
          <RatingBadge value={product.rating} />
        </div>
        <div className="productActions">
          <button disabled={product.stock <= 0} onClick={handleAdd} type="button">
            <ShoppingCart size={17} /> {product.stock <= 0 ? "Out of Stock" : isAuthenticated ? "Add" : "Login Required to Buy"}
          </button>
          <button aria-label="Save to wishlist" className="wishlistButton" onClick={handleWishlist} type="button"><Heart size={17} /></button>
        </div>
      </div>
    </motion.article>
  );
}
