import { useState } from "react";

export default function NotificationDropdown({ trigger }) {
  const [open, setOpen] = useState(false);
  const items = ["Weather sync ready", "2 cart items awaiting checkout", "AI prediction reports are saved"];

  return (
    <div className="dropdownWrap">
      <button aria-label="Notifications" className="iconButton" onClick={() => setOpen((value) => !value)} type="button">
        {trigger}
      </button>
      {open && (
        <div className="dropdownPanel">
          <strong>Notifications</strong>
          {items.map((item) => <span key={item}>{item}</span>)}
        </div>
      )}
    </div>
  );
}
