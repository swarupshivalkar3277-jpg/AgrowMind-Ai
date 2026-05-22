import { createContext, createElement, useContext, useEffect, useMemo, useState } from "react";

import { getProfile, googleAuth, loginUser, logoutUser, registerUser } from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(token));

  useEffect(() => {
    let ignore = false;

    async function loadProfile() {
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }

      try {
        const { data } = await getProfile();
        if (!ignore) {
          setUser(data.user);
        }
      } catch {
        localStorage.removeItem("token");
        if (!ignore) {
          setToken(null);
          setUser(null);
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    loadProfile();

    return () => {
      ignore = true;
    };
  }, [token]);

  async function register(payload) {
    const { data } = await registerUser(payload);
    return data;
  }

  async function login(email, password, otp_code = "") {
    const { data } = await loginUser({ email, password, otp_code });
    localStorage.setItem("token", data.access_token);
    setToken(data.access_token);
    return data;
  }

  async function loginWithGoogle(idToken, role = "user") {
    const { data } = await googleAuth({ id_token: idToken, role });
    localStorage.setItem("token", data.access_token);
    setToken(data.access_token);
    return data;
  }

  async function logout() {
    try {
      await logoutUser();
    } finally {
      localStorage.removeItem("token");
      setToken(null);
      setUser(null);
    }
  }

  const value = useMemo(
    () => ({
      isAuthenticated: Boolean(token),
      loading,
      login,
      loginWithGoogle,
      logout,
      register,
      token,
      user,
    }),
    [loading, token, user]
  );

  return createElement(AuthContext.Provider, { value }, children);
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
