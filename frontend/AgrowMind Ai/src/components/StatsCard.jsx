export default function StatsCard({ icon: Icon, label, value, tone = "green" }) {
  return (
    <article className={`statsCard ${tone}`}>
      {Icon && <Icon size={22} />}
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}
