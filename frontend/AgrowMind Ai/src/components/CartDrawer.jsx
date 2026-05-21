import { Link } from "react-router-dom";

import { useCart } from "../context/CartContext";

export default function CartDrawer() {
  const { cart, drawerOpen, remove, setDrawerOpen, update } = useCart();

  return (
    <div className={`cartOverlay ${drawerOpen ? "open" : ""}`} onClick={() => setDrawerOpen(false)}>
      <aside className="cartDrawer" onClick={(event) => event.stopPropagation()}>
        <div className="sectionHeader">
          <h2>Your Cart</h2>
          <button className="textButton" onClick={() => setDrawerOpen(false)} type="button">Close</button>
        </div>
        <div className="cartItems">
          {cart.items.map((item) => (
            <article key={item.product.id} className="cartItem">
              <img alt={item.product.name} src={item.product.image} />
              <div>
                <strong>{item.product.name}</strong>
                <span>₹{item.product.price}</span>
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
          <span>Subtotal ₹{cart.subtotal}</span>
          <span>Tax ₹{cart.tax}</span>
          <span>Shipping ₹{cart.shipping}</span>
          <strong>Total ₹{cart.total}</strong>
          <Link className="primaryButton" onClick={() => setDrawerOpen(false)} to="/cart">Open Cart</Link>
        </div>
      </aside>
    </div>
  );
}
