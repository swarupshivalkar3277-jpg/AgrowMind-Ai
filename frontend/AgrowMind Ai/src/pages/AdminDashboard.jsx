import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, BarChart3, Boxes, PackageCheck, ShieldCheck, Users, WalletCards } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import StatsCard from "../components/StatsCard";
import { getAdminAnalytics, getAdminOrders, getAdminUsers, getProducts } from "../services/authService";

export default function AdminDashboard() {
  const [analytics, setAnalytics] = useState(null);
  const [orders, setOrders] = useState([]);
  const [users, setUsers] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getAdminAnalytics(), getAdminOrders(), getAdminUsers(), getProducts()])
      .then(([analyticsResult, orderResult, userResult, productResult]) => {
        setAnalytics(analyticsResult.data.data || {});
        setOrders(orderResult.data.data?.items || []);
        setUsers(userResult.data.data?.items || []);
        setProducts(productResult.data.items || []);
      })
      .catch((err) => setError(err?.response?.data?.detail || "Admin data failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <main className="stateScreen premiumLoader">
        <div className="skeletonStack"><i /><i /><i /></div>
        <h1>Loading admin dashboard</h1>
      </main>
    );
  }

  const revenueData = orders.slice(0, 8).reverse().map((order, index) => ({ name: `O${index + 1}`, revenue: Number(order.total || 0) }));
  const activity = [
    ...orders.slice(0, 3).map((order) => ({ id: order.id, label: `Order #${order.id.slice(-8)} moved to ${order.order_status}`, meta: `Rs. ${order.total}` })),
    ...users.slice(0, 2).map((target) => ({ id: target.id, label: `${target.name} joined as ${target.role}`, meta: target.email })),
  ];

  return (
    <main className="pageStack">
      <section className="pageHero compactHero">
        <div>
          <span className="eyebrowText">Admin Dashboard</span>
          <h1>Platform control center</h1>
          <p>Monitor users, crop intelligence, revenue, inventory, marketplace health, and operational activity.</p>
          <div className="heroMeta">
            <span>Revenue Rs. {analytics?.total_revenue ?? 0}</span>
            <span>{analytics?.total_users ?? 0} users</span>
            <span>{analytics?.total_ai_predictions ?? 0} predictions</span>
          </div>
        </div>
        <Link className="primaryButton" to="/admin/products/add">Add Product</Link>
      </section>

      {error && <div className="alert">{error}</div>}

      <section className="statsGrid">
        <StatsCard icon={Users} label="Total users" value={analytics?.total_users ?? 0} />
        <StatsCard icon={ShieldCheck} label="Farmers" value={analytics?.total_farmers ?? 0} tone="teal" />
        <StatsCard icon={Activity} label="Total predictions" value={analytics?.total_ai_predictions ?? 0} tone="blue" />
        <StatsCard icon={WalletCards} label="Revenue" value={`Rs. ${analytics?.total_revenue ?? 0}`} tone="emerald" />
        <StatsCard icon={Boxes} label="Products" value={products.length} tone="amber" />
        <StatsCard icon={PackageCheck} label="Orders" value={analytics?.total_orders ?? 0} tone="violet" />
      </section>

      <section className="analyticsGrid">
        <article className="panel chartPanel">
          <div className="sectionHeader"><div><span className="eyebrowText">Predictions</span><h2>Predictions by crop</h2></div></div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={analytics?.top_crops || []}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" fill="#16A34A" radius={[6, 6, 0, 0]} /></BarChart>
          </ResponsiveContainer>
        </article>
        <article className="panel chartPanel">
          <div className="sectionHeader"><div><span className="eyebrowText">Diseases</span><h2>Most common diseases</h2></div></div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={analytics?.top_diseases || []}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" fill="#84CC16" radius={[6, 6, 0, 0]} /></BarChart>
          </ResponsiveContainer>
        </article>
        <article className="panel chartPanel">
          <div className="sectionHeader"><div><span className="eyebrowText">Marketplace</span><h2>Performance</h2></div></div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={revenueData}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis /><Tooltip /><Line type="monotone" dataKey="revenue" stroke="#22C55E" strokeWidth={3} dot={false} /></LineChart>
          </ResponsiveContainer>
        </article>
        <article className="panel chartPanel">
          <div className="sectionHeader"><div><span className="eyebrowText">Growth</span><h2>User growth</h2></div></div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={users.slice(0, 8).reverse().map((_, index) => ({ name: `U${index + 1}`, users: index + 1 }))}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Line type="monotone" dataKey="users" stroke="#0F172A" strokeWidth={3} dot={false} /></LineChart>
          </ResponsiveContainer>
        </article>
      </section>

      <section className="panel">
        <div className="sectionHeader"><div><span className="eyebrowText">Recent Activity</span><h2>Operational feed</h2></div><BarChart3 size={22} /></div>
        <div className="activityList">
          {activity.map((item) => <article key={item.id}><strong>{item.label}</strong><span>{item.meta}</span></article>)}
          {activity.length === 0 && <div className="emptyState">No platform activity yet.</div>}
        </div>
      </section>
    </main>
  );
}
