import { ShieldCheck, SlidersHorizontal } from "lucide-react";

export default function AdminSettings() {
  return (
    <main className="pageStack">
      <section className="pageHero compactHero"><div><span className="eyebrowText">Admin Settings</span><h1>Platform configuration</h1><p>Security posture, protected operations, marketplace controls, and operational preferences.</p></div></section>
      <section className="settingsGrid">
        <article className="panel insightCard"><ShieldCheck size={24} /><h2>Security</h2><p>Admin routes are protected by role-based access. Keep OTP and admin secret workflows server-side.</p></article>
        <article className="panel insightCard"><SlidersHorizontal size={24} /><h2>Operations</h2><p>Configure low-stock thresholds, order escalation rules, and future RAG assistant settings.</p></article>
      </section>
    </main>
  );
}
