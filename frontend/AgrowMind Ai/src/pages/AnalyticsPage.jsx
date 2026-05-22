import AnalyticsCard from "../components/AnalyticsCard";
import StatsCard from "../components/StatsCard";
import { Activity, Leaf, ShoppingBag, TrendingUp } from "lucide-react";

export default function AnalyticsPage() {
  return (
    <main className="pageStack">
      <section className="pageHero compactHero">
        <div>
          <span className="eyebrowText">Analytics</span>
          <h1>Farm and marketplace intelligence</h1>
          <p>Monitor disease trends, recommendation impact, inventory movement, and order health.</p>
        </div>
      </section>
      <section className="statsGrid">
        <StatsCard icon={Leaf} label="Healthy scans" value="68%" />
        <StatsCard icon={Activity} label="High-risk scans" value="12" tone="teal" />
        <StatsCard icon={ShoppingBag} label="Products matched" value="124" tone="blue" />
        <StatsCard icon={TrendingUp} label="Recovery score" value="81%" tone="emerald" />
      </section>
      <AnalyticsCard />
    </main>
  );
}
