export default function NotificationsPage() {
  const items = ["Prediction completed successfully", "Razorpay order verification enabled", "Admin inventory needs stock review"];
  return (
    <main className="pageStack">
      <section className="pageHero compactHero">
        <div>
          <span className="eyebrowText">Notifications</span>
          <h1>Operational alerts</h1>
          <p>AI, marketplace, order, inventory, and payment updates appear here.</p>
        </div>
      </section>
      <section className="adminList">
        {items.map((item) => <article key={item}><span>{item}</span><strong>Now</strong></article>)}
      </section>
    </main>
  );
}
