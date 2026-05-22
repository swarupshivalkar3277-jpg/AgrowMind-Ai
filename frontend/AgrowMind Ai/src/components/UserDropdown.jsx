import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function UserDropdown({ user }) {
  const [open, setOpen] = useState(false);
  const { logout } = useAuth();
  const initials = user?.name?.slice(0, 2)?.toUpperCase() || "AI";

  return (
    <div className="dropdownWrap">
      <button className="avatarButton" onClick={() => setOpen((value) => !value)} type="button">{initials}</button>
      {open && (
        <div className="dropdownPanel userPanel">
          <strong>{user?.name || "AgroMind User"}</strong>
          <small>{user?.email}</small>
          <Link to="/settings">Settings</Link>
          <button onClick={logout} type="button">Logout</button>
        </div>
      )}
    </div>
  );
}
