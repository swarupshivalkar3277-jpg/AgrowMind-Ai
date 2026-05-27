import { NavLink } from "react-router-dom";
import { Bot, Home, ScanSearch, ShoppingBag, UserRound } from "lucide-react";

const items = [
  { to: "/dashboard", label: "Home", icon: Home },
  { to: "/diagnose", label: "Diagnose", icon: ScanSearch },
  { to: "/marketplace", label: "Market", icon: ShoppingBag },
  { to: "/assistant", label: "AI", icon: Bot },
  { to: "/settings", label: "Profile", icon: UserRound },
];

export default function MobileBottomNavbar() {
  return (
    <nav className="mobileBottomNav" aria-label="Primary mobile navigation">
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
