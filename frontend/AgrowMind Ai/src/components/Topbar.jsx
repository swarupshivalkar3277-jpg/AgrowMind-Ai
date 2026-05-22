import { Link } from "react-router-dom";
import { Bell, Menu, Search, ShoppingCart } from "lucide-react";

import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import NotificationDropdown from "./NotificationDropdown";
import UserDropdown from "./UserDropdown";

export default function Topbar({ onMenu }) {
  const { cart, setDrawerOpen } = useCart();
  const { user } = useAuth();

  return (
    <header className="appTopbar">
      <button aria-label="Open sidebar" className="iconButton mobileOnly" onClick={onMenu} type="button">
        <Menu size={21} />
      </button>
      <label className="topSearch">
        <Search size={18} />
        <input placeholder="Search products, orders, crop history" type="search" />
      </label>
      <div className="topbarRight">
        <Link className="quickSellButton" to="/sell">Sell</Link>
        <button aria-label="Open cart" className="iconButton cartIcon" onClick={() => setDrawerOpen(true)} type="button">
          <ShoppingCart size={20} />
          <span>{cart.count || 0}</span>
        </button>
        <NotificationDropdown trigger={<Bell size={20} />} />
        <UserDropdown user={user} />
      </div>
    </header>
  );
}
