import { useEffect, useState } from "react";

import { Link } from "react-router-dom";
import { Heart } from "lucide-react";

import EmptyState from "../components/EmptyState";
import ProductCard from "../components/ProductCard";
import { getWishlist } from "../services/authService";

export default function WishlistPage() {
  const [products, setProducts] = useState([]);

  useEffect(() => {
    getWishlist().then(({ data }) => setProducts(data.items || [])).catch(() => setProducts([]));
  }, []);

  return (
    <main className="pageStack">
      <section className="pageHero compactHero">
        <div>
          <span className="eyebrowText">Wishlist</span>
          <h1>Saved marketplace products</h1>
          <p>Track fertilizers, seeds, pesticides, tools, and saplings before checkout.</p>
        </div>
      </section>
      <section className="productGrid">
        {products.map((product) => <ProductCard key={product.id} product={product} />)}
      </section>
      {products.length === 0 && (
        <EmptyState
          action={<Link className="primaryButton" to="/marketplace">Find Products</Link>}
          icon={Heart}
          title="No saved products yet"
          text="Save fertilizers, seeds, pesticides, tools, and saplings while comparing options."
        />
      )}
    </main>
  );
}
