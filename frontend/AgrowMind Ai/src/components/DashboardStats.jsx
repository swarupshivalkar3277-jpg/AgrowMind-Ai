import { Activity, Leaf, PackageCheck, TrendingUp } from "lucide-react";

import StatsCard from "./StatsCard";

export default function DashboardStats({ historyCount = 0 }) {
  return (
    <section className="statsGrid">
      <StatsCard icon={Leaf} label="Crops Monitored" value="3" />
      <StatsCard icon={Activity} label="Predictions" value={historyCount} tone="teal" />
      <StatsCard icon={TrendingUp} label="AI Confidence" value="92%" tone="blue" />
      <StatsCard icon={PackageCheck} label="Market Matches" value="24+" tone="emerald" />
    </section>
  );
}
