import { Download, FileText, ShoppingBag, Sprout, Table2 } from "lucide-react";

export default function ReportsPage() {
  return (
    <main className="pageStack">
      <section className="pageHero compactHero"><div><span className="eyebrowText">Reports</span><h1>Professional farm reports</h1><p>Prediction, marketplace, farmer activity, and analytics reports with charts, tables, and AgroMind branding.</p></div></section>
      <section className="reportGrid">
        {[
          ["Prediction Report", "Diagnosis history, confidence, severity, treatment, and prevention.", Sprout],
          ["Marketplace Report", "Orders, spend, products, and purchase history.", ShoppingBag],
          ["Farmer Activity Report", "Scans, saved reports, recent purchases, and recommendations.", Table2],
          ["Admin Analytics Report", "Investor-ready platform metrics for admins.", FileText],
        ].map(([title, text, Icon]) => <article className="panel reportCard" key={title}><Icon size={24} /><h2>{title}</h2><p>{text}</p><button className="secondaryButton" type="button"><Download size={16} /> Export PDF</button></article>)}
      </section>
    </main>
  );
}
