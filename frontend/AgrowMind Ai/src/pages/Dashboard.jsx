import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Bot, CalendarClock, CloudSun, FileText, History, ScanSearch, ShoppingBag, UserRound } from "lucide-react";

import DashboardStats from "../components/DashboardStats";
import WeatherCard from "../components/WeatherCard";
import { useAuth } from "../context/AuthContext";
import { getHistory, getOrders } from "../services/authService";

const quickActions = [
  { to: "/diagnose", label: "Detect Disease", icon: ScanSearch },
  { to: "/marketplace", label: "Marketplace", icon: ShoppingBag },
  { to: "/history", label: "History", icon: History },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/assistant", label: "Ask AI", icon: Bot },
];

export default function Dashboard() {
  const { user } = useAuth();
  const [history, setHistory] = useState([]);
  const [orders, setOrders] = useState([]);
  const now = useMemo(() => new Date(), []);

  useEffect(() => {
    getHistory().then(({ data }) => setHistory(data.items || [])).catch(() => setHistory([]));
    getOrders().then(({ data }) => setOrders(data.items || [])).catch(() => setOrders([]));
  }, []);

  const recentDiseases = history.slice(0, 3);
  const recentOrders = orders.slice(0, 3);

  return (
    <main className="pageStack">
      <motion.section className="dashboardHero farmerHero" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}>
        <div>
          <span className="eyebrowText">Farmer Workspace</span>
          <h1>Welcome back, {user?.name || "farmer"}</h1>
          <p>Your mobile-first command center for crop scans, saved reports, orders, weather, and AI farming guidance.</p>
          <div className="heroMeta">
            <span><CalendarClock size={17} /> {now.toLocaleDateString()} {now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
            <span><CloudSun size={17} /> Weather-aware crop advice</span>
          </div>
        </div>
        <article className="profileSummary">
          <UserRound size={28} />
          <strong>{user?.name}</strong>
          <span>{user?.role || "farmer"} account</span>
          <small>{user?.email}</small>
        </article>
      </motion.section>

      <section className="quickActionGrid" aria-label="Quick actions">
        {quickActions.map((action) => {
          const Icon = action.icon;
          return (
            <Link className="quickActionCard" key={action.label} to={action.to}>
              <Icon size={22} />
              <span>{action.label}</span>
            </Link>
          );
        })}
      </section>

      <DashboardStats historyCount={history.length} orderCount={orders.length} />

      <section className="overviewGrid">
        <section className="panel softPanel">
          <div className="sectionHeader">
            <div><span className="eyebrowText">Activity Feed</span><h2>Recent diagnoses</h2></div>
            <Link className="textButton" to="/history">View all</Link>
          </div>
          <div className="activityList">
            {recentDiseases.map((item) => (
              <article key={item.id}>
                <strong>{item.prediction?.disease?.replaceAll("_", " ") || "Crop scan"}</strong>
                <span>{item.crop} • {Math.round(Number(item.prediction?.confidence || 0))}% confidence</span>
              </article>
            ))}
            {recentDiseases.length === 0 && <div className="emptyState">No scans yet. Start with your first AI diagnosis.</div>}
          </div>
        </section>

        <section className="panel softPanel">
          <div className="sectionHeader">
            <div><span className="eyebrowText">Purchases</span><h2>Recent orders</h2></div>
            <Link className="textButton" to="/orders">View all</Link>
          </div>
          <div className="activityList">
            {recentOrders.map((order) => (
              <article key={order.id}>
                <strong>Order #{order.id.slice(-8)}</strong>
                <span>Rs. {order.total} • {order.order_status}</span>
              </article>
            ))}
            {recentOrders.length === 0 && <div className="emptyState">No purchases yet. Recommended inputs will appear after checkout.</div>}
          </div>
        </section>

        <WeatherCard />
      </section>
    </main>
  );
}
