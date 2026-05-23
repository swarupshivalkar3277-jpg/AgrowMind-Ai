import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";

import { useAuth } from "../context/AuthContext";

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
let googleInitializedClientId = "";

export default function GoogleAuthButton({ role = "farmer" }) {
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

      window.agromindGoogleSignIn = async (response) => {
        try {
          await loginWithGoogle(response.credential, role);
          toast.success("Signed in with Google");
        } catch (err) {
          setError(err?.response?.data?.detail || "Google sign-in failed");
        }
      };

      if (googleInitializedClientId !== googleClientId) {
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: (response) => window.agromindGoogleSignIn?.(response),
        });
        googleInitializedClientId = googleClientId;
      }

      if (buttonRef.current.dataset.rendered === "true") {
        return;
      }

      buttonRef.current.innerHTML = "";
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: "outline",
        size: "large",
        width: buttonRef.current.offsetWidth || 320,
      });
      buttonRef.current.dataset.rendered = "true";
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
