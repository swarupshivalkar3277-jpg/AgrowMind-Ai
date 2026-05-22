import { useAuth } from "../context/AuthContext";

export default function SettingsPage({ darkMode, onToggleTheme }) {
  const { user } = useAuth();
  return (
    <main className="pageStack">
      <section className="pageHero compactHero">
        <div>
          <span className="eyebrowText">Settings</span>
          <h1>Workspace preferences</h1>
          <p>Manage profile, appearance, notifications, and account controls.</p>
        </div>
      </section>
      <section className="settingsGrid">
        <article className="panel checkoutForm">
          <h2>Profile</h2>
          <label><span>Name</span><input readOnly value={user?.name || ""} /></label>
          <label><span>Email</span><input readOnly value={user?.email || ""} /></label>
          <label><span>Role</span><input readOnly value={user?.role || ""} /></label>
        </article>
        <article className="panel checkoutForm">
          <h2>Appearance</h2>
          <button className="secondaryButton" onClick={onToggleTheme} type="button">{darkMode ? "Use light mode" : "Use dark mode"}</button>
          <label><span>Notifications</span><select defaultValue="important"><option value="important">Important only</option><option value="all">All updates</option></select></label>
        </article>
      </section>
    </main>
  );
}
