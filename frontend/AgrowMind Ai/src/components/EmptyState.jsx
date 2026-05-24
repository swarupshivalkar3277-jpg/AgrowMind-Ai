import { Leaf } from "lucide-react";

export default function EmptyState({ action, icon: Icon = Leaf, text, title = "Nothing here yet" }) {
  return (
    <section className="emptyState emptyStateBrand" role="status">
      <div className="emptyStateIcon">
        <Icon size={26} />
      </div>
      <div>
        <h2>{title}</h2>
        {text && <p>{text}</p>}
      </div>
      {action}
    </section>
  );
}
