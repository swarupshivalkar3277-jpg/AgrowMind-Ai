import { Link, useNavigate } from "react-router-dom";
import { Heart, ShoppingCart, Star } from "lucide-react";
import toast from "react-hot-toast";

import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { toggleWishlist } from "../services/authService";

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

  return (
    <article className="productCard">
      <Link className="productImageLink" to={`/marketplace/product/${product.id}`}>
        <div className="productBadgeStack">
          {Number(product.rating || 0) >= 4.5 && <span>Bestseller</span>}
          {product.featured && <span>Featured</span>}
          {product.stock > 0 && product.stock <= 5 && <span>Low stock</span>}
        </div>
        <img alt={product.name} src={product.image || "https://images.unsplash.com/photo-1464226184884-fa280b87c399?auto=format&fit=crop&w=900&q=80"} />
      </Link>
      <div className="productCardBody">
        <div>
          <span className="productCategory">{product.category}</span>
          <h3>{product.name}</h3>
          <p>{product.description}</p>
          <small className="mutedText">{product.unit_size || product.unit || "1 piece"}</small>
          {product.stock <= 0 && <span className="alert">Out of Stock</span>}
        </div>
        <div className="productMeta">
          <strong>Rs. {product.price}</strong>
          <span><Star size={15} fill="currentColor" /> {product.rating}</span>
        </div>
        <div className="productActions">
          <button disabled={product.stock <= 0} onClick={handleAdd} type="button">
            <ShoppingCart size={17} /> {product.stock <= 0 ? "Out of Stock" : isAuthenticated ? "Add" : "Login Required to Buy"}
          </button>
          <button className="iconTextButton" onClick={handleWishlist} type="button"><Heart size={17} /> Save</button>
        </div>
      </div>
    </article>
  );
}
