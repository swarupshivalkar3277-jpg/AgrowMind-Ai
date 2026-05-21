import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useCart } from "../context/CartContext";
import { useAuth } from "../context/AuthContext";
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
    if (goCheckout) {
      navigate("/checkout");
    }
  }

  if (!product) {
    return <main className="marketPage"><div className="analysisLoader"><span /><strong>Loading product...</strong></div></main>;
  }

  return (
    <main className="marketPage">
      <section className="productDetail panel">
        <img alt={product.name} src={product.image} />
        <div>
          <Link className="backButton" to="/marketplace">Back to Marketplace</Link>
          <span className="productCategory">{product.category}</span>
          <h1>{product.name}</h1>
          <p>{product.description}</p>
          <div className="productMeta detailMeta">
            <strong>₹{product.price}</strong>
            <span>★ {product.rating}</span>
            <span>{product.stock} in stock</span>
          </div>
          <label className="quantityInput">
            <span>Quantity</span>
            <input min="1" onChange={(event) => setQuantity(Number(event.target.value))} type="number" value={quantity} />
          </label>
          <div className="heroActions">
            <button className="primaryButton" onClick={() => addAndMaybeCheckout(false)} type="button">Add to Cart</button>
            <button className="secondaryButton" onClick={() => addAndMaybeCheckout(true)} type="button">Buy Now</button>
          </div>
        </div>
      </section>
    </main>
  );
}
