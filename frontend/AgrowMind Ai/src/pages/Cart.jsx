import { Link } from "react-router-dom";

import { useCart } from "../context/CartContext";

export default function Cart() {
  const { cart, remove, update } = useCart();

  return (
    <main className="pageStack">
      <section className="panel cartPage">
        <div className="sectionHeader">
          <h1>Shopping Cart</h1>
          <Link className="secondaryButton" to="/marketplace">Continue Shopping</Link>
        </div>
        <div className="cartLayout">
          <div className="cartItems">
            {cart.items.map((item) => (
              <article className="cartItem large" key={item.product.id}>
                <img alt={item.product.name} src={item.product.image} />
                <div>
                  <strong>{item.product.name}</strong>
                  <span>Rs. {item.product.price} each</span>
                  <div className="quantityControl">
                    <button onClick={() => update(item.product.id, item.quantity - 1)} type="button">-</button>
                    <span>{item.quantity}</span>
                    <button onClick={() => update(item.product.id, item.quantity + 1)} type="button">+</button>
                  </div>
                </div>
                <strong>Rs. {item.line_total}</strong>
                <button className="iconTextButton" onClick={() => remove(item.product.id)} type="button">Remove</button>
              </article>
            ))}
            {cart.items.length === 0 && <p>Your cart is empty.</p>}
          </div>
          <aside className="orderSummary">
            <h2>Order Summary</h2>
            <span>Subtotal Rs. {cart.subtotal}</span>
            <span>Tax Rs. {cart.tax}</span>
            <span>Delivery Rs. {cart.shipping}</span>
            <strong>Total Rs. {cart.total}</strong>
            <Link className="primaryButton" to="/checkout">Checkout</Link>
          </aside>
        </div>
      </section>
    </main>
  );
}
