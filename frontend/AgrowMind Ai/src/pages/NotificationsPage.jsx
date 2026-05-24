import { Bell, CloudSun, Megaphone, PackageCheck, Sparkles } from "lucide-react";

import EmptyState from "../components/EmptyState";

export default function NotificationsPage() {
  const items = [
    { icon: Sparkles, title: "Prediction completed", text: "Your latest crop diagnosis report is ready.", time: "Now" },
    { icon: PackageCheck, title: "Order update", text: "Razorpay verification is active for secure checkout.", time: "Today" },
    { icon: CloudSun, title: "Weather alert", text: "High humidity can increase leaf disease spread.", time: "Today" },
    { icon: Megaphone, title: "Admin announcement", text: "Inventory review is recommended for low stock products.", time: "This week" },
  ];
  return (
    <main className="pageStack">
      <section className="pageHero compactHero">
        <div>
          <span className="eyebrowText">Notifications</span>
          <h1>Operational alerts</h1>
          <p>AI, marketplace, order, inventory, and payment updates appear here.</p>
        </div>
      </section>
      <section className="notificationList">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <article key={item.title}>
              <Icon size={21} />
              <div><strong>{item.title}</strong><span>{item.text}</span></div>
              <small>{item.time}</small>
            </article>
          );
        })}
        {items.length === 0 && <EmptyState icon={Bell} title="No notifications" text="Order updates, weather alerts, predictions, and admin announcements will appear here." />}
      </section>
    </main>
  );
}
