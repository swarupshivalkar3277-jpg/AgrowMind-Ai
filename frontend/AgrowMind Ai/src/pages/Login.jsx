import { useState } from "react";

import { useAuth } from "../context/AuthContext";

function normalizeError(error) {
  return error?.response?.data?.detail || error?.message || "Login failed";
}

export default function Login({ onHome, onSwitch }) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await login(email, password);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="authPanel">
      <button className="backButton" onClick={onHome} type="button">
        Back to home
      </button>
      <p className="eyebrow">Welcome Back</p>
      <h1>AgroMind AI</h1>
      <form className="authForm" onSubmit={handleSubmit}>
        <label>
          <span>Email</span>
          <input
            autoComplete="email"
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            value={email}
          />
        </label>
        <label>
          <span>Password</span>
          <input
            autoComplete="current-password"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>
        {error && <div className="alert">{error}</div>}
        <button disabled={submitting} type="submit">
          {submitting ? "Signing in..." : "Login"}
        </button>
      </form>
      <button className="textButton" onClick={onSwitch} type="button">
        Create an account
      </button>
    </section>
  );
}
