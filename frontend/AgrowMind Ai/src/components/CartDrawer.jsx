import { Link } from "react-router-dom";
import { X } from "lucide-react";

import { useCart } from "../context/CartContext";

export default function CartDrawer() {
  const { cart, drawerOpen, remove, setDrawerOpen, update } = useCart();

  return (
    <div className={`cartOverlay ${drawerOpen ? "open" : ""}`} onClick={() => setDrawerOpen(false)}>
      <aside className="cartDrawer" onClick={(event) => event.stopPropagation()}>
        <div className="sectionHeader">
          <h2>Your Cart</h2>
          <button aria-label="Close cart" className="iconButton" onClick={() => setDrawerOpen(false)} type="button"><X size={18} /></button>
        </div>
        <div className="cartItems">
          {cart.items.map((item) => (
            <article className="cartItem" key={item.product.id}>
              <img alt={item.product.name} src={item.product.image} />
              <div>
                <strong>{item.product.name}</strong>
                <span>Rs. {item.product.price} / {item.product.unit_size || item.product.unit || "piece"}</span>
                <div className="quantityControl">
                  <button onClick={() => update(item.product.id, item.quantity - 1)} type="button">-</button>
                  <span>{item.quantity}</span>
                  <button onClick={() => update(item.product.id, item.quantity + 1)} type="button">+</button>
                </div>
              </div>
              <button className="iconTextButton" onClick={() => remove(item.product.id)} type="button">Remove</button>
            </article>
          ))}
          {cart.items.length === 0 && <p>Your cart is empty.</p>}
        </div>
        <div className="cartSummary">
          <span>Subtotal Rs. {cart.subtotal}</span>
          <span>Tax Rs. {cart.tax}</span>
          <span>Shipping Rs. {cart.shipping}</span>
          <strong>Total Rs. {cart.total}</strong>
          <Link className="primaryButton" onClick={() => setDrawerOpen(false)} to="/cart">Open Cart</Link>
        </div>
      </aside>
    </div>
  );
}
