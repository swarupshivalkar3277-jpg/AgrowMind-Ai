export default function RecommendationCard({ icon: Icon, items = [], text, title }) {
  return (
    <article className="recommendationCard">
      {Icon && <Icon size={22} />}
      <strong>{title}</strong>
      {text && <p>{text}</p>}
      {items?.length > 0 && (
        <div className="chipList">
          {items.slice(0, 5).map((item) => <span key={item}>{item}</span>)}
        </div>
      )}
    </article>
  );
}
