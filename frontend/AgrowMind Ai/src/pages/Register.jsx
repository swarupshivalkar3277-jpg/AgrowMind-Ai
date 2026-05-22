import { useState } from "react";
import toast from "react-hot-toast";

import { useAuth } from "../context/AuthContext";
import GoogleAuthButton from "../components/GoogleAuthButton";
import { sendOtp } from "../services/authService";

function normalizeError(error) {
  const detail = error?.response?.data?.detail || error?.response?.data?.error;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).filter(Boolean).join(", ");
  }

  return error?.message || "Registration failed";
}

export default function Register({ onHome, onSwitch }) {
  const { register } = useAuth();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    role: "user",
    otp_code: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sendingOtp, setSendingOtp] = useState(false);
  const [otpMessage, setOtpMessage] = useState("");

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSendOtp() {
    setError("");
    setOtpMessage("");
    setSendingOtp(true);
    try {
      await sendOtp({ email: form.email, purpose: "register" });
      setOtpMessage("OTP sent to your email.");
      toast.success("OTP sent to your email");
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setSendingOtp(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await register(form);
      toast.success("Registration successful. Please login.");
      onSwitch();
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
      <p className="eyebrow">Start Securely</p>
      <h1>Create Account</h1>
      <form className="authForm" onSubmit={handleSubmit}>
        <label>
          <span>Name</span>
          <input
            autoComplete="name"
            minLength="2"
            onChange={(event) => updateField("name", event.target.value)}
            required
            value={form.name}
          />
        </label>
        <label>
          <span>Email</span>
          <input
            autoComplete="email"
            onChange={(event) => updateField("email", event.target.value)}
            required
            type="email"
            value={form.email}
          />
        </label>
        <label>
          <span>Password</span>
          <input
            autoComplete="new-password"
            minLength="6"
            onChange={(event) => updateField("password", event.target.value)}
            required
            type="password"
            value={form.password}
          />
        </label>
        <div className="otpRow">
          <label>
            <span>Email OTP</span>
            <input
              onChange={(event) => updateField("otp_code", event.target.value)}
              placeholder="6 digit OTP"
              required
              value={form.otp_code}
            />
          </label>
          <button className="secondaryButton" disabled={!form.email || sendingOtp} onClick={handleSendOtp} type="button">
            {sendingOtp ? "Sending..." : "Send OTP"}
          </button>
        </div>
        {otpMessage && <div className="successAlert">{otpMessage}</div>}
        <label>
          <span>Role</span>
          <select onChange={(event) => updateField("role", event.target.value)} value={form.role}>
            <option value="user">User</option>
            <option value="farmer">Farmer</option>
            <option value="seller">Seller</option>
            <option value="buyer">Buyer</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        {error && <div className="alert">{error}</div>}
        <button disabled={submitting} type="submit">
          {submitting ? "Creating..." : "Register"}
        </button>
      </form>
      <button className="textButton" onClick={onSwitch} type="button">
        Already have an account
      </button>
      <GoogleAuthButton role={form.role} />
    </section>
  );
}
