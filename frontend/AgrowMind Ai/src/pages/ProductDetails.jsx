import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";

import PublicNav from "../components/PublicNav";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { getProduct } from "../services/authService";

export default function ProductDetails() {
  const { id } = useParams();
  const { add } = useCart();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [quantity, setQuantity] = useState(1);

  useEffect(() => {
    getProduct(id).then(({ data }) => setProduct(data.product));
  }, [id]);

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
    if (goCheckout) navigate("/checkout");
  }

  if (!product) {
    return <main className="publicPage"><PublicNav /><div className="pageStack"><div className="analysisLoader"><span /><strong>Loading product...</strong></div></div></main>;
  }

  const image = product.image || "https://images.unsplash.com/photo-1464226184884-fa280b87c399?auto=format&fit=crop&w=1200&q=80";

  return (
    <main className="publicPage">
      <PublicNav />
      <div className="pageStack">
      <section className="productDetail panel">
        <div>
          <img alt={product.name} className="mainProductImage" src={image} />
          <div className="galleryRail">
            {[image, image, image].map((item, index) => <img alt={`${product.name} ${index + 1}`} key={index} src={item} />)}
          </div>
        </div>
        <div>
          <Link className="backButton" to="/marketplace">Back to Marketplace</Link>
          <span className="productCategory">{product.category}</span>
          <h1>{product.name}</h1>
          <p>{product.description}</p>
          <div className="productMeta detailMeta">
            <strong>Rs. {product.price}</strong>
            <span>Rating {product.rating}/5</span>
            <span>{product.stock} in stock</span>
            <span>Store: {product.seller_name}</span>
          </div>
          {product.stock <= 0 && <div className="alert">Out of Stock</div>}
          <label className="quantityInput">
            <span>Quantity</span>
            <input max={Math.max(product.stock, 1)} min="1" onChange={(event) => setQuantity(Number(event.target.value))} type="number" value={quantity} />
          </label>
          <div className="heroActions">
            <button className="primaryButton" disabled={product.stock <= 0} onClick={() => addAndMaybeCheckout(false)} type="button">
              {product.stock <= 0 ? "Out of Stock" : isAuthenticated ? "Add to Cart" : "Login Required to Buy"}
            </button>
            <button className="secondaryButton" disabled={product.stock <= 0} onClick={() => addAndMaybeCheckout(true)} type="button">
              {product.stock <= 0 ? "Out of Stock" : isAuthenticated ? "Buy Now" : "Login to Checkout"}
            </button>
          </div>
          <section className="reviewsBox">
            <h2>Reviews</h2>
            <p>Verified customer reviews, product questions, and related products will appear here.</p>
          </section>
        </div>
      </section>
      </div>
    </main>
  );
}
