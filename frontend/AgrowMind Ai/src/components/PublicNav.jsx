import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function PublicNav() {
  const { isAuthenticated } = useAuth();

  return (
    <nav className="siteNav" aria-label="Primary navigation">
      <Link className="brandButton" to="/">
        AgroMind AI
      </Link>
      <div className="navActions">
        <Link to="/">Home</Link>
        <Link to="/marketplace">Marketplace</Link>
        {isAuthenticated ? (
          <Link className="primaryButton" to="/dashboard">Dashboard</Link>
        ) : (
          <>
            <Link className="secondaryButton" to="/login">Login</Link>
            <Link className="primaryButton" to="/register">Register</Link>
          </>
        )}
      </div>
    </nav>
  );
}
