import { NavLink } from "react-router-dom";
import { BarChart3, History, Home, ShoppingBag, ShoppingCart } from "lucide-react";

const items = [
  { to: "/dashboard", label: "Home", icon: Home },
  { to: "/marketplace", label: "Shop", icon: ShoppingBag },
  { to: "/history", label: "History", icon: History },
  { to: "/analytics", label: "Stats", icon: BarChart3 },
  { to: "/cart", label: "Cart", icon: ShoppingCart },
];

export default function MobileBottomNavbar() {
  return (
    <nav className="mobileBottomNav">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink key={item.label} to={item.to}>
            <Icon size={20} />
            <span>{item.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
