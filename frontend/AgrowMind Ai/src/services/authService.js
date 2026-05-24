import axios from "axios";

export const API_BASE =
  (
    import.meta.env.VITE_API_BASE ||
    import.meta.env.VITE_API_URL ||
    "http://127.0.0.1:8000"
  ).replace(/\/+$/, "");

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  withCredentials: false,
});

const GET_CACHE_TTL_MS = 60_000;
const getCache = new Map();

function cacheKey(url, params = {}) {
  const query = new URLSearchParams(
    Object.entries(params)
      .filter(([, value]) => value !== undefined && value !== null && value !== "")
      .sort(([left], [right]) => left.localeCompare(right))
  ).toString();
  return query ? `${url}?${query}` : url;
}

function clearGetCache() {
  getCache.clear();
}

function cachedGet(url, config = {}) {
  const key = cacheKey(url, config.params);
  const cached = getCache.get(key);

  if (cached && Date.now() - cached.createdAt < GET_CACHE_TTL_MS) {
    return Promise.resolve(cached.response);
  }

  return api.get(url, config).then((response) => {
    getCache.set(key, { createdAt: Date.now(), response });
    return response;
  });
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => {
    if (response.config?.method && response.config.method !== "get") {
      clearGetCache();
    }
    return response;
  },
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem("token");
      window.dispatchEvent(new Event("agromind:unauthorized"));
    }

    return Promise.reject(error);
  }
);

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

export function sendOtp(payload) {
  return api.post("/auth/send-otp", payload, {
    headers: {
      "Content-Type": "application/json",
    },
  });
}

export function forgotPassword(payload) {
  return api.post("/auth/forgot-password", payload);
}

export function googleAuth(payload) {
  return api.post("/auth/google", payload, {
    headers: {
      "Content-Type": "application/json",
    },
  });
}

export function logoutUser() {
  return api.post("/auth/logout");
}

export function getProfile() {
  return cachedGet("/profile");
}

export function getHistory() {
  return cachedGet("/history");
}

export function getProducts(params = {}) {
  return cachedGet("/marketplace/products", { params });
}

export function getProduct(productId) {
  return cachedGet(`/marketplace/products/${productId}`);
}

export function createProduct(payload) {
  return api.post("/marketplace/products", payload);
}

export function updateProduct(productId, payload) {
  return api.put(`/marketplace/products/${productId}`, payload);
}

export function deleteProduct(productId) {
  return api.delete(`/marketplace/products/${productId}`);
}

export function getSellerProducts() {
  return cachedGet("/marketplace/products");
}

export function getCart() {
  return cachedGet("/marketplace/cart");
}

export function addCartItem(productId, quantity = 1) {
  return api.post("/marketplace/cart/items", { product_id: productId, quantity });
}

export function updateCartItem(productId, quantity) {
  return api.put(`/marketplace/cart/items/${productId}`, { product_id: productId, quantity });
}

export function removeCartItem(productId) {
  return api.delete(`/marketplace/cart/items/${productId}`);
}

export function toggleWishlist(productId) {
  return api.post(`/marketplace/wishlist/${productId}`);
}

export function getWishlist() {
  return cachedGet("/marketplace/wishlist");
}

export function checkoutCart(payload) {
  return api.post("/marketplace/checkout", payload);
}

export function createRazorpayOrder(payload = {}) {
  return api.post("/marketplace/payment/razorpay-order", payload);
}

export function verifyRazorpayPayment(payload) {
  return api.post("/marketplace/payment/verify", payload);
}

export function getOrders() {
  return cachedGet("/marketplace/orders");
}

export function cancelOrder(orderId) {
  return api.delete(`/marketplace/orders/${orderId}`);
}

export function requestOrderRefund(orderId) {
  return api.post(`/marketplace/orders/${orderId}/refund`);
}

export function getAdminOrders() {
  return cachedGet("/admin/orders");
}

export function updateAdminOrderStatus(orderId, statusValue) {
  return api.patch(`/admin/orders/${orderId}/status`, null, {
    params: { status_value: statusValue },
  });
}

export function getAdminAnalytics() {
  return cachedGet("/admin/analytics");
}

export function getAdminUsers(params = {}) {
  return cachedGet("/admin/users", { params });
}

export function deleteAdminUser(userId) {
  return api.delete(`/admin/users/${userId}`);
}

export function blockAdminUser(userId, blocked) {
  return api.patch(`/admin/users/${userId}/block`, { blocked });
}

export function updateAdminUserRole(userId, role) {
  return api.patch(`/admin/users/${userId}/role`, { role });
}

export function createAdminProduct(payload) {
  return api.post("/admin/products", payload);
}

export function updateAdminProduct(productId, payload) {
  return api.put(`/admin/products/${productId}`, payload);
}

export function deleteAdminProduct(productId) {
  return api.delete(`/admin/products/${productId}`);
}

export default api;
