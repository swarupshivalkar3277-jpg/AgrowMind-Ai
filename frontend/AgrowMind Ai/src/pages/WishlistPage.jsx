import { useEffect, useState } from "react";

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
      {products.length === 0 && <div className="emptyMarket">No wishlist products yet.</div>}
    </main>
  );
}
