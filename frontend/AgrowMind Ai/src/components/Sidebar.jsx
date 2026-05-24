import { NavLink } from "react-router-dom";
import {
  BarChart3,
  Bot,
  Boxes,
  CloudSun,
  FileText,
  Heart,
  History,
  Home,
  LogOut,
  PackageCheck,
  Settings,
  ShieldCheck,
  ShoppingCart,
  ScanSearch,
  Store,
  UserCog,
  WalletCards,
  X,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";

const commonLinks = [
  { to: "/dashboard", label: "Dashboard", icon: Home },
  { to: "/diagnose", label: "Diagnose", icon: ScanSearch },
  { to: "/marketplace", label: "Marketplace", icon: Store },
  { to: "/history", label: "Prediction History", icon: History },
  { to: "/orders", label: "Orders", icon: PackageCheck },
  { to: "/wishlist", label: "Wishlist", icon: Heart },
  { to: "/cart", label: "Cart", icon: ShoppingCart },
  { to: "/weather", label: "Weather", icon: CloudSun },
  { to: "/assistant", label: "AI Assistant", icon: Bot },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/settings", label: "Settings", icon: Settings },
];

const adminLinks = [
  { to: "/admin/dashboard", label: "Admin Dashboard", icon: ShieldCheck },
  { to: "/admin/users", label: "Users", icon: UserCog },
  { to: "/admin/products", label: "Products", icon: Boxes },
  { to: "/admin/orders", label: "Orders", icon: PackageCheck },
  { to: "/admin/predictions", label: "AI Predictions", icon: BarChart3 },
  { to: "/admin/analytics", label: "Analytics", icon: WalletCards },
  { to: "/admin/reports", label: "Reports", icon: FileText },
  { to: "/admin/settings", label: "Admin Settings", icon: Settings },
];

function SidebarLink({ item, onClose }) {
  const Icon = item.icon;
  return (
    <NavLink className="sidebarLink" onClick={onClose} to={item.to}>
      <Icon size={19} />
      <span>{item.label}</span>
    </NavLink>
  );
}

export default function Sidebar({ open, onClose }) {
  const { logout, user } = useAuth();
  const isAdmin = user?.role === "admin";

  return (
    <>
      <div className={`sidebarScrim ${open ? "show" : ""}`} onClick={onClose} />
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="sidebarHeader">
          <div className="brandMark">AI</div>
          <div>
            <strong>AgroMind AI</strong>
            <span>Crop SaaS + Marketplace</span>
          </div>
          <button aria-label="Close sidebar" className="iconButton mobileOnly" onClick={onClose} type="button">
            <X size={18} />
          </button>
        </div>
        <nav className="sidebarNav">
          {commonLinks.map((item) => <SidebarLink item={item} key={item.label} onClose={onClose} />)}
          {isAdmin && <p className="sidebarGroup">Admin</p>}
          {isAdmin && adminLinks.map((item) => <SidebarLink item={item} key={item.label} onClose={onClose} />)}
        </nav>
        <button className="logoutButton" onClick={logout} type="button">
          <LogOut size={18} />
          <span>Logout</span>
        </button>
      </aside>
    </>
  );
}
