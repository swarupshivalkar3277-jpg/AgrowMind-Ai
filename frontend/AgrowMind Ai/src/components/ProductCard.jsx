import { Link, useNavigate } from "react-router-dom";

import { useCart } from "../context/CartContext";
import { useAuth } from "../context/AuthContext";
import { toggleWishlist } from "../services/authService";

export default function ProductCard({ product }) {
  const { add } = useCart();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  async function handleAdd() {
    if (!isAuthenticated) {
      navigate("/login");
      return;
    }
    await add(product.id, 1);
  }

  async function handleWishlist() {
    if (!isAuthenticated) {
      navigate("/login");
      return;
    }
    await toggleWishlist(product.id);
  }

  return (
    <article className="productCard">
      <Link to={`/marketplace/product/${product.id}`}>
        <img alt={product.name} src={product.image} />
      </Link>
      <div className="productCardBody">
        <div>
          <span className="productCategory">{product.category}</span>
          <h3>{product.name}</h3>
          <p>{product.description}</p>
        </div>
        <div className="productMeta">
          <strong>₹{product.price}</strong>
          <span>★ {product.rating}</span>
        </div>
        <div className="productActions">
          <button onClick={handleAdd} type="button">Add to Cart</button>
          <button className="iconTextButton" onClick={handleWishlist} type="button">Wishlist</button>
        </div>
      </div>
    </article>
  );
}
