import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Leaf, Mail, ShieldCheck, Smartphone } from "lucide-react";
import toast from "react-hot-toast";

import { useAuth } from "../context/AuthContext";
import GoogleAuthButton from "../components/GoogleAuthButton";
import { forgotPassword, sendOtp } from "../services/authService";

function normalizeError(error) {
  const detail = error?.response?.data?.detail || error?.response?.data?.error;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).filter(Boolean).join(", ");
  }

  return error?.message || "Login failed";
}

export default function Login({ onHome, onSwitch, startForgot = false }) {
  const { login } = useAuth();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [forgotMode, setForgotMode] = useState(startForgot);
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sendingOtp, setSendingOtp] = useState(false);
  const [otpCooldown, setOtpCooldown] = useState(0);
  const otpDigits = Array.from({ length: 6 }, (_, index) => otpCode[index] || "");

  useEffect(() => {
    if (!otpCooldown) {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      setOtpCooldown((seconds) => Math.max(seconds - 1, 0));
    }, 1000);

    return () => window.clearTimeout(timer);
  }, [otpCooldown]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      if (forgotMode) {
        await forgotPassword({ email, otp_code: otpCode, new_password: newPassword });
        setMessage("Password reset. You can login now.");
        toast.success("Password reset. You can login now.");
        setForgotMode(false);
        return;
      }

      await login(email, password, otpCode);
      toast.success("Welcome back");
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSendOtp(purpose = "login") {
    setError("");
    setMessage("");
    setSendingOtp(true);
    try {
      await sendOtp({ email, purpose });
      setMessage("OTP sent to your email.");
      toast.success("OTP sent to your email");
      setOtpCooldown(60);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setSendingOtp(false);
    }
  }

  return (
    <section className="marketAuthShell">
      <motion.aside className="authWelcome" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <button className="backButton" onClick={onHome} type="button">Back to home</button>
        <div className="authLogo"><Leaf size={26} /><strong>AgroMind</strong></div>
        <h1>{forgotMode ? "Reset securely with OTP" : "Welcome to AgroMind Marketplace"}</h1>
        <p>Buy verified farm inputs, track orders, and get AI-matched recommendations for tomato, mango, and coconut crops.</p>
        <div className="authIllustration">
          <span><ShieldCheck size={22} /> Secure payments</span>
          <span><CheckCircle2 size={22} /> Verified sellers</span>
          <span><Smartphone size={22} /> OTP protected login</span>
        </div>
      </motion.aside>
      <motion.div className="authPanel premiumAuthPanel" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}>
      <p className="eyebrow">{forgotMode ? "Reset Password" : "Welcome Back"}</p>
      <h1>{forgotMode ? "Forgot Password" : "Login"}</h1>
      <div className="loginTabs">
        <button className="active" type="button"><Mail size={16} /> Email</button>
        <button type="button"><Smartphone size={16} /> Mobile OTP</button>
      </div>
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
        {!forgotMode && (
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
        )}
        {forgotMode && (
          <label>
            <span>New Password</span>
            <input
              autoComplete="new-password"
              minLength="6"
              onChange={(event) => setNewPassword(event.target.value)}
              required
              type="password"
              value={newPassword}
            />
          </label>
        )}
        <div className="otpRow">
          <label>
            <span>Email OTP</span>
            <input
              autoComplete="one-time-code"
              inputMode="numeric"
              maxLength="8"
              onChange={(event) => setOtpCode(event.target.value.replace(/\D/g, "").slice(0, 8))}
              pattern="[0-9]{4,8}"
              placeholder="6 digit OTP"
              required
              type="text"
              value={otpCode}
            />
          </label>
          <button className="secondaryButton" disabled={!email || sendingOtp || otpCooldown > 0} onClick={() => handleSendOtp(forgotMode ? "forgot_password" : "login")} type="button">
            {sendingOtp ? "Sending..." : otpCooldown > 0 ? `Wait ${otpCooldown}s` : "Send OTP"}
          </button>
        </div>
        <div className="otpBoxes" aria-hidden="true">{otpDigits.map((digit, index) => <span key={index}>{digit}</span>)}</div>
        <AnimatePresence>
          {message && <motion.div className="successAlert" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>{message}</motion.div>}
          {(error || searchParams.get("error")) && <motion.div className="alert" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>{error || searchParams.get("error")}</motion.div>}
        </AnimatePresence>
        <button className="primaryButton" disabled={submitting} type="submit">
          {submitting ? "Please wait..." : forgotMode ? "Reset Password" : "Login"}
        </button>
      </form>
      <button className="textButton" onClick={() => { setForgotMode((current) => !current); setError(""); setMessage(""); }} type="button">
        {forgotMode ? "Back to login" : "Forgot password"}
      </button>
      {!forgotMode && <Link className="textButton" to="/forgot-password">Reset with OTP</Link>}
      <button className="textButton" onClick={onSwitch} type="button">
        Create an account
      </button>
      {!forgotMode && <GoogleAuthButton />}
      </motion.div>
    </section>
  );
}
