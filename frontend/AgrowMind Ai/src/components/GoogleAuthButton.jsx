import { useEffect, useRef, useState } from "react";

import { useAuth } from "../context/AuthContext";

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

export default function GoogleAuthButton({ role = "user" }) {
  const buttonRef = useRef(null);
  const { loginWithGoogle } = useAuth();
  const [error, setError] = useState("");

  useEffect(() => {
    if (!googleClientId) {
      return;
    }

    const scriptId = "google-identity-services";
    const initialize = () => {
      if (!window.google || !buttonRef.current) {
        return;
      }

      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: async (response) => {
          try {
            await loginWithGoogle(response.credential, role);
          } catch (err) {
            setError(err?.response?.data?.detail || "Google sign-in failed");
          }
        },
      });
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: "outline",
        size: "large",
        width: buttonRef.current.offsetWidth || 320,
      });
    };

    if (!document.getElementById(scriptId)) {
      const script = document.createElement("script");
      script.id = scriptId;
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.onload = initialize;
      document.head.appendChild(script);
    } else {
      initialize();
    }
  }, [loginWithGoogle, role]);

  if (!googleClientId) {
    return <div className="apiStatus authHint">Add VITE_GOOGLE_CLIENT_ID to enable Google sign-in.</div>;
  }

  return (
    <div className="googleAuthBlock">
      <div ref={buttonRef} />
      {error && <div className="alert">{error}</div>}
    </div>
  );
}
