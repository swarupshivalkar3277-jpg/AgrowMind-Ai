import { Link } from "react-router-dom";

import ProductCard from "./ProductCard";

export default function MarketplacePreview({ products = [] }) {
  return (
    <section className="pageSection">
      <div className="sectionHeader">
        <div>
          <span className="eyebrowText">Marketplace</span>
          <h2>Suggested farm inputs</h2>
        </div>
        <Link className="secondaryButton" to="/marketplace">View all</Link>
      </div>
      <div className="productGrid compact">
        {products.slice(0, 4).map((product) => <ProductCard key={product.id} product={product} />)}
      </div>
    </section>
  );
}
