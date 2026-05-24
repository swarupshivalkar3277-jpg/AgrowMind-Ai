import { useState } from "react";
import { CloudSun, PackageCheck, Sparkles } from "lucide-react";

export default function NotificationDropdown({ trigger }) {
  const [open, setOpen] = useState(false);
  const items = [
    { icon: CloudSun, label: "Weather sync ready", meta: "Local advisory updated" },
    { icon: PackageCheck, label: "Cart awaiting checkout", meta: "Review stock before payment" },
    { icon: Sparkles, label: "AI prediction reports saved", meta: "PDF export available" },
  ];

  return (
    <div className="dropdownWrap">
      <button aria-label="Notifications" className="iconButton" onClick={() => setOpen((value) => !value)} type="button">
        {trigger}
      </button>
      {open && (
        <div className="dropdownPanel">
          <strong>Notifications</strong>
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <span className="dropdownNotification" key={item.label}>
                <Icon size={17} />
                <span><strong>{item.label}</strong><small>{item.meta}</small></span>
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
