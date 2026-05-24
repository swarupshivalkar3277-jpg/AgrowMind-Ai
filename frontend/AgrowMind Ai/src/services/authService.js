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

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
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
  return api.get("/profile");
}

export function getHistory() {
  return api.get("/history");
}

export function getProducts(params = {}) {
  return api.get("/marketplace/products", { params });
}

export function getProduct(productId) {
  return api.get(`/marketplace/products/${productId}`);
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
  return api.get("/marketplace/products");
}

export function getCart() {
  return api.get("/marketplace/cart");
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
  return api.get("/marketplace/wishlist");
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
  return api.get("/marketplace/orders");
}

export function cancelOrder(orderId) {
  return api.delete(`/marketplace/orders/${orderId}`);
}

export function getAdminOrders() {
  return api.get("/admin/orders");
}

export function updateAdminOrderStatus(orderId, statusValue) {
  return api.patch(`/admin/orders/${orderId}/status`, null, {
    params: { status_value: statusValue },
  });
}

export function getAdminAnalytics() {
  return api.get("/admin/analytics");
}

export function getAdminUsers(params = {}) {
  return api.get("/admin/users", { params });
}

export function deleteAdminUser(userId) {
  return api.delete(`/admin/users/${userId}`);
}

export function blockAdminUser(userId, blocked) {
  return api.patch(`/admin/users/${userId}/block`, { blocked });
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
