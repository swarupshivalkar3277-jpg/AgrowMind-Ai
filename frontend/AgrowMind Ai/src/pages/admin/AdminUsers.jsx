import { useEffect, useState } from "react";
import { Search, ShieldCheck, Trash2 } from "lucide-react";
import toast from "react-hot-toast";

import { blockAdminUser, deleteAdminUser, getAdminUsers, updateAdminUserRole } from "../../services/authService";
import { useAuth } from "../../context/AuthContext";

export default function AdminUsers() {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState("");

  async function refresh() {
    const { data } = await getAdminUsers({ search });
    setUsers(data.data?.items || []);
  }

  useEffect(() => { refresh().catch(() => setUsers([])); }, []);

  async function toggleBlock(target) {
    await blockAdminUser(target.id, !target.blocked);
    toast.success(target.blocked ? "User unblocked" : "User blocked");
    await refresh();
  }

  async function changeRole(target, role) {
    await updateAdminUserRole(target.id, role);
    toast.success("Role updated");
    await refresh();
  }

  async function remove(target) {
    await deleteAdminUser(target.id);
    toast.success("User deleted");
    await refresh();
  }

  return (
    <main className="pageStack">
      <section className="pageHero compactHero"><div><span className="eyebrowText">User Management</span><h1>Farmers and administrators</h1><p>Search, block, unblock, delete, and change roles from a protected admin-only page.</p></div></section>
      <form className="panel toolbarPanel" onSubmit={(event) => { event.preventDefault(); refresh(); }}>
        <label className="searchInput"><Search size={18} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by name or email" /></label>
        <button className="secondaryButton" type="submit">Search</button>
      </form>
      <section className="adminTable panel">
        {users.map((target) => (
          <article key={target.id}>
            <div><strong>{target.name}</strong><span>{target.email}</span></div>
            <select disabled={target.id === user?.id} value={target.role} onChange={(event) => changeRole(target, event.target.value)}><option value="farmer">farmer</option><option value="admin">admin</option></select>
            <button className="iconTextButton" disabled={target.id === user?.id} onClick={() => toggleBlock(target)} type="button"><ShieldCheck size={16} /> {target.blocked ? "Unblock" : "Block"}</button>
            <button className="iconTextButton dangerText" disabled={target.id === user?.id} onClick={() => remove(target)} type="button"><Trash2 size={16} /> Delete</button>
          </article>
        ))}
        {users.length === 0 && <div className="emptyState">No users found.</div>}
      </section>
    </main>
  );
}
