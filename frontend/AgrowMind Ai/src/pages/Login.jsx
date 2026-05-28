import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, CheckCircle2, KeyRound, Leaf, Mail, ShieldCheck, Smartphone } from "lucide-react";
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
  const [otpSent, setOtpSent] = useState(false);
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
      setOtpSent(true);
      setOtpCooldown(60);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setSendingOtp(false);
    }
  }

  return (
    <section className="marketAuthShell advancedLoginShell">
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
      <motion.div className="authPanel premiumAuthPanel flipAuthPanel" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}>
      <p className="eyebrow">{forgotMode ? "Reset Password" : "Secure Login"}</p>
      <h1>{forgotMode ? "Reset access" : "Login to continue"}</h1>
      <div className="loginStepper" aria-label="Login progress">
        <span className="active"><Mail size={16} /> Details</span>
        <i />
        <span className={otpSent ? "active" : ""}><KeyRound size={16} /> OTP</span>
      </div>
      <form className="authForm" onSubmit={handleSubmit}>
        <motion.div className="loginStage" layout>
          <label>
            <span>Email</span>
            <input
              autoComplete="email"
              onChange={(event) => { setEmail(event.target.value); setOtpSent(false); setOtpCode(""); }}
              placeholder="farmer@example.com"
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
                onChange={(event) => { setPassword(event.target.value); setOtpSent(false); setOtpCode(""); }}
                placeholder="Enter password"
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
                placeholder="Create new password"
                required
                type="password"
                value={newPassword}
              />
            </label>
          )}
          <button className="otpSendButton" disabled={!email || (!forgotMode && !password) || sendingOtp || otpCooldown > 0} onClick={() => handleSendOtp(forgotMode ? "forgot_password" : "login")} type="button">
            {sendingOtp ? "Sending OTP..." : otpCooldown > 0 ? `Resend in ${otpCooldown}s` : <>Send OTP <ArrowRight size={17} /></>}
          </button>
        </motion.div>
        <AnimatePresence initial={false}>
          {otpSent && (
            <motion.div
              animate={{ opacity: 1, y: 0, height: "auto" }}
              className="otpStage"
              exit={{ opacity: 0, y: -8, height: 0 }}
              initial={{ opacity: 0, y: 8, height: 0 }}
            >
              <div className="otpStageHead">
                <span><ShieldCheck size={17} /> OTP sent</span>
                <button disabled={sendingOtp || otpCooldown > 0} onClick={() => handleSendOtp(forgotMode ? "forgot_password" : "login")} type="button">
                  {otpCooldown > 0 ? `${otpCooldown}s` : "Resend"}
                </button>
              </div>
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
              <div className="otpBoxes" aria-hidden="true">{otpDigits.map((digit, index) => <span key={index}>{digit}</span>)}</div>
            </motion.div>
          )}
        </AnimatePresence>
        {!otpSent && (
          <div className="otpHint">
            <Smartphone size={17} />
            <span>Enter email and password first. The OTP section opens after sending verification.</span>
          </div>
        )}
        <AnimatePresence>
          {message && <motion.div className="successAlert" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>{message}</motion.div>}
          {(error || searchParams.get("error")) && <motion.div className="alert" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>{error || searchParams.get("error")}</motion.div>}
        </AnimatePresence>
        <button className="primaryButton" disabled={submitting || !otpSent} type="submit">
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
