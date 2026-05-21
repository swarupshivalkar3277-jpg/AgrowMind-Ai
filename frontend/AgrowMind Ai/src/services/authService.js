import axios from "axios";

export const API_BASE =
  (
    import.meta.env.VITE_API_BASE ||
    import.meta.env.VITE_API_URL ||
    "http://127.0.0.1:8000"
  ).replace(/\/+$/, "");

const api = axios.create({
  baseURL: API_BASE,
  timeout: 45000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

export function registerUser(payload) {
  return api.post("/auth/register", payload, {
    headers: {
      "Content-Type": "application/json",
    },
  });
}

export function loginUser(payload) {
  return api.post("/auth/login", payload, {
    headers: {
      "Content-Type": "application/json",
    },
  });
}

export function logoutUser() {
  return api.post("/auth/logout");
}

export function getProfile() {
  return api.get("/profile");
}

export function getHistory() {
  return api.get("/history");
}

export default api;
