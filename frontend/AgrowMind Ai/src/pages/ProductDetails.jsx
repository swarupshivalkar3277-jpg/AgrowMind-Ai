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
    getProduct(id).then(({ data }) => {
      const nextProduct = data.product;
      setProduct(nextProduct);
      const stored = JSON.parse(localStorage.getItem("agromind:recent-products") || "[]");
      const next = [nextProduct, ...stored.filter((item) => item.id !== nextProduct.id)].slice(0, 6);
      localStorage.setItem("agromind:recent-products", JSON.stringify(next));
    });
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
    return (
      <main className="publicPage">
        <PublicNav />
        <div className="pageStack">
          <div className="analysisLoader premiumLoader">
            <div className="skeletonStack"><i /><i /><i /></div>
            <strong>Loading product...</strong>
          </div>
        </div>
      </main>
    );
  }

  const image = product.image || "https://images.unsplash.com/photo-1464226184884-fa280b87c399?auto=format&fit=crop&w=1200&q=80";
  const gallery = [image, ...(product.gallery || [])].filter(Boolean).slice(0, 6);

  return (
    <main className="publicPage">
      <PublicNav />
      <div className="pageStack">
      <section className="productDetail panel">
        <div>
          <img alt={product.name} className="mainProductImage" src={image} />
          <div className="galleryRail">
            {gallery.map((item, index) => <img alt={`${product.name} ${index + 1}`} key={index} src={item} />)}
          </div>
        </div>
        <div>
          <Link className="backButton" to="/marketplace">Back to Marketplace</Link>
          <span className="productCategory">{product.category}</span>
          <h1>{product.name}</h1>
          <p>{product.short_description || product.description}</p>
          <div className="productMeta detailMeta">
            <strong>Rs. {product.price}</strong>
            {product.mrp > product.price && <span>MRP Rs. {product.mrp}</span>}
            <span>Rating {product.rating}/5</span>
            <span>{product.stock} in stock</span>
            <span>Store: {product.seller_name}</span>
          </div>
          <div className="productTrustRow">
            <span>AI matched</span>
            <span>Safe checkout</span>
            <span>Verified seller</span>
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
          <section className="productInfoTabs">
            <article><h2>Description</h2><p>{product.description || product.short_description}</p></article>
            <article><h2>Benefits</h2><ul>{(product.benefits || []).map((item) => <li key={item}>{item}</li>)}</ul></article>
            <article><h2>Usage</h2><p>{product.usage_instructions || "Follow label instructions and local agricultural guidance."}</p></article>
            <article><h2>Precautions</h2><p>{product.precautions || "Use protective equipment and avoid over-application."}</p></article>
          </section>
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
