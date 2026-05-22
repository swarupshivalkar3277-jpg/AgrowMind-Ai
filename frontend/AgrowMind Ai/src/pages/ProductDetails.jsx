import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

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
    if (!isAuthenticated) {
      navigate("/login");
      return;
    }
    await add(product.id, quantity);
    if (goCheckout) navigate("/checkout");
  }

  if (!product) {
    return <main className="pageStack"><div className="analysisLoader"><span /><strong>Loading product...</strong></div></main>;
  }

  const image = product.image || "https://images.unsplash.com/photo-1464226184884-fa280b87c399?auto=format&fit=crop&w=1200&q=80";

  return (
    <main className="pageStack">
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
            <span>Seller: {product.seller_name}</span>
          </div>
          <label className="quantityInput">
            <span>Quantity</span>
            <input min="1" onChange={(event) => setQuantity(Number(event.target.value))} type="number" value={quantity} />
          </label>
          <div className="heroActions">
            <button className="primaryButton" onClick={() => addAndMaybeCheckout(false)} type="button">Add to Cart</button>
            <button className="secondaryButton" onClick={() => addAndMaybeCheckout(true)} type="button">Buy Now</button>
          </div>
          <section className="reviewsBox">
            <h2>Reviews</h2>
            <p>Verified buyer reviews, seller questions, and related products will appear here.</p>
          </section>
        </div>
      </section>
    </main>
  );
}
