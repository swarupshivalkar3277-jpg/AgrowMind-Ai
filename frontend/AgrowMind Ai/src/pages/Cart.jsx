import { Link } from "react-router-dom";
import { Heart, Percent, ShieldCheck, Trash2 } from "lucide-react";

import EmptyState from "../components/EmptyState";
import { PriceBlock } from "../components/MarketplaceUI";
import { useCart } from "../context/CartContext";

export default function Cart() {
  const { cart, remove, update } = useCart();
  const hasInvalidItems = cart.items.some((item) => item.product.stock <= 0 || item.quantity > item.product.stock);
  const mrpTotal = cart.items.reduce((sum, item) => sum + Number(item.product.mrp || item.product.price || 0) * item.quantity, 0);
  const discount = Math.max(0, mrpTotal - cart.subtotal);

  return (
    <main className="pageStack shopAccountPage">
      <section className="shopPageHeader">
        <div><span>Secure cart</span><h1>Review your farm inputs</h1></div>
        <Link className="secondaryButton" to="/marketplace">Continue Shopping</Link>
      </section>
      {cart.items.length === 0 ? (
        <EmptyState title="Your cart is empty" text="Add seeds, fertilizers, crop protection, or tools to start checkout." action={<Link className="primaryButton" to="/marketplace">Browse Marketplace</Link>} />
      ) : (
        <section className="premiumCartLayout">
          <div className="cartItemsPanel">
            {cart.items.map((item) => (
              <article className="premiumCartItem" key={item.product.id}>
                <img alt={item.product.name} src={item.product.image} />
                <div className="cartItemInfo">
                  <span>{item.product.category}</span>
                  <strong>{item.product.name}</strong>
                  <small>{item.product.unit_size || item.product.unit || "1 piece"} - Delivery in 2-5 days</small>
                  {item.product.stock <= 0 && <span className="alert">Out of Stock</span>}
                  {item.quantity > item.product.stock && item.product.stock > 0 && <span className="alert">Only {item.product.stock} available</span>}
                  <PriceBlock price={item.product.price} mrp={item.product.mrp} />
                  <div className="cartItemActions">
                    <div className="quantityStepper">
                      <button aria-label="Decrease quantity" onClick={() => update(item.product.id, item.quantity - 1)} type="button">-</button>
                      <span>{item.quantity}</span>
                      <button aria-label="Increase quantity" disabled={item.quantity >= item.product.stock} onClick={() => update(item.product.id, item.quantity + 1)} type="button">+</button>
                    </div>
                    <button type="button"><Heart size={16} /> Save for later</button>
                    <button onClick={() => remove(item.product.id)} type="button"><Trash2 size={16} /> Remove</button>
                  </div>
                </div>
                <strong>Rs. {item.line_total}</strong>
              </article>
            ))}
          </div>
          <aside className="premiumSummary">
            <div className="couponBox"><Percent size={18} /><span>Apply seasonal farm coupons at payment</span></div>
            <h2>Price Summary</h2>
            <span><small>MRP</small><strong>Rs. {mrpTotal.toFixed(2)}</strong></span>
            <span><small>Discount</small><strong>- Rs. {discount.toFixed(2)}</strong></span>
            <span><small>Delivery</small><strong>Rs. {cart.shipping}</strong></span>
            <span><small>Taxes</small><strong>Rs. {cart.tax}</strong></span>
            <span className="summaryTotal"><small>Final Total</small><strong>Rs. {cart.total}</strong></span>
            <p><ShieldCheck size={16} /> Safe checkout. Stock is reduced only after confirmed payment.</p>
            {hasInvalidItems ? <span className="alert">Fix unavailable items before checkout.</span> : <Link className="primaryButton stickyCheckout" to="/checkout">Proceed to Checkout</Link>}
          </aside>
        </section>
      )}
    </main>
  );
}
