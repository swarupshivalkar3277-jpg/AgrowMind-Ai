import { NavLink } from "react-router-dom";
import { History, Home, ScanSearch, ShoppingBag, UserRound } from "lucide-react";

const items = [
  { to: "/dashboard", label: "Home", icon: Home },
  { to: "/diagnose", label: "Diagnose", icon: ScanSearch },
  { to: "/marketplace", label: "Market", icon: ShoppingBag },
  { to: "/history", label: "History", icon: History },
  { to: "/settings", label: "Profile", icon: UserRound },
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
