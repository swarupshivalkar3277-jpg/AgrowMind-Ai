import { useState } from "react";
import { Outlet } from "react-router-dom";

import CartDrawer from "./CartDrawer";
import FloatingActionButton from "./FloatingActionButton";
import MobileBottomNavbar from "./MobileBottomNavbar";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export default function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="appShell">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="appMain">
        <Topbar onMenu={() => setSidebarOpen(true)} />
        <Outlet />
      </div>
      <FloatingActionButton />
      <MobileBottomNavbar />
      <CartDrawer />
    </div>
  );
}
