import { FileText, LineChart, Table2 } from "lucide-react";

export default function AdminReports() {
  return (
    <main className="pageStack">
      <section className="pageHero compactHero"><div><span className="eyebrowText">Admin Reports</span><h1>Professional export center</h1><p>Analytics, marketplace, farmer activity, and prediction summaries prepared for branded PDF workflows.</p></div></section>
      <section className="reportGrid">
        {[
          ["Admin Analytics Report", "Users, revenue, predictions, crops, and disease trends.", LineChart],
          ["Marketplace Report", "Orders, revenue, stock, low inventory, and product performance.", Table2],
          ["Farmer Activity Report", "Registrations, prediction history, orders, and engagement.", FileText],
        ].map(([title, text, Icon]) => <article className="panel reportCard" key={title}><Icon size={24} /><h2>{title}</h2><p>{text}</p><button className="secondaryButton" type="button">Prepare PDF</button></article>)}
      </section>
    </main>
  );
}
