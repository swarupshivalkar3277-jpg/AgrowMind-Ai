import { Link, NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";

export default function MarketplaceNav({ darkMode, onToggleTheme }) {
  const { isAuthenticated, logout, user } = useAuth();
  const { cart, setDrawerOpen } = useCart();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  return (
    <nav className="siteNav marketNav">
      <Link className="brandButton" to="/">AgroMind AI</Link>
      <div className="navActions">
        <NavLink to="/dashboard">Dashboard</NavLink>
        <NavLink to="/marketplace">Marketplace</NavLink>
        <NavLink to="/orders">My Orders</NavLink>
        {user?.role === "admin" && <NavLink to="/admin">Admin</NavLink>}
        <button className="cartButton" onClick={() => setDrawerOpen(true)} type="button">
          Cart <span>{cart.count || 0}</span>
        </button>
        {isAuthenticated ? (
          <button className="secondaryButton" onClick={handleLogout} type="button">Logout</button>
        ) : (
          <Link className="secondaryButton" to="/login">Login</Link>
        )}
        <button aria-label="Toggle theme" className="themeToggle" onClick={onToggleTheme} type="button">
          {darkMode ? "Light" : "Dark"}
        </button>
      </div>
    </nav>
  );
}
