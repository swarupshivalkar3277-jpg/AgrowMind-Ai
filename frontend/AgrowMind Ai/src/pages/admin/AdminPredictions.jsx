import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { getAdminAnalytics } from "../../services/authService";

export default function AdminPredictions() {
  const [analytics, setAnalytics] = useState({});

  useEffect(() => { getAdminAnalytics().then(({ data }) => setAnalytics(data.data || {})).catch(() => setAnalytics({})); }, []);

  const stats = useMemo(() => [
    { label: "Total predictions", value: analytics.total_ai_predictions || 0 },
    { label: "Crop groups", value: analytics.top_crops?.length || 0 },
    { label: "Disease classes", value: analytics.top_diseases?.length || 0 },
  ], [analytics]);

  return (
    <main className="pageStack">
      <section className="pageHero compactHero"><div><span className="eyebrowText">AI Analytics</span><h1>Prediction intelligence</h1><p>Disease, crop, and prediction-history analytics for model and advisory decisions.</p></div></section>
      <section className="statsGrid">{stats.map((item) => <article className="statsCard" key={item.label}><span>{item.label}</span><strong>{item.value}</strong></article>)}</section>
      <section className="analyticsGrid">
        <article className="panel chartPanel"><h2>Diseases</h2><ResponsiveContainer width="100%" height={300}><BarChart data={analytics.top_diseases || []}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" fill="#16A34A" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></article>
        <article className="panel chartPanel"><h2>Crops</h2><ResponsiveContainer width="100%" height={300}><BarChart data={analytics.top_crops || []}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" fill="#84CC16" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></article>
      </section>
    </main>
  );
}
