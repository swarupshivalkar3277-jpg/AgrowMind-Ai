import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";

import AppShell from "./components/AppShell";
import ErrorBoundary from "./components/ErrorBoundary";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { CartProvider } from "./context/CartContext";
import AdminDashboard from "./pages/AdminDashboard";
import AnalyticsPage from "./pages/AnalyticsPage";
import Cart from "./pages/Cart";
import Checkout from "./pages/Checkout";
import Dashboard from "./pages/Dashboard";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import Home from "./pages/Home";
import HistoryPage from "./pages/HistoryPage";
import Login from "./pages/Login";
import Marketplace from "./pages/Marketplace";
import NotificationsPage from "./pages/NotificationsPage";
import Orders from "./pages/Orders";
import PaymentStatus from "./pages/PaymentStatus";
import ProductDetails from "./pages/ProductDetails";
import Register from "./pages/Register";
import SellerDashboard from "./pages/SellerDashboard";
import SellProductsPage from "./pages/SellProductsPage";
import SettingsPage from "./pages/SettingsPage";
import WishlistPage from "./pages/WishlistPage";

function LoadingScreen({ label = "Loading secure workspace..." }) {
  return (
    <main className="stateScreen">
      <span className="spinner" />
      <h1>AgroMind AI</h1>
      <p>{label}</p>
    </main>
  );
}

function ProtectedRoute({ children, adminOnly = false, sellerOnly = false }) {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();

  if (loading) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return <Navigate replace to="/login" state={{ from: location.pathname }} />;
  }

  if (adminOnly && user?.role !== "admin") {
    return <Navigate replace to="/dashboard" />;
  }

  if (sellerOnly && !["admin", "farmer", "seller"].includes(user?.role)) {
    return <Navigate replace to="/marketplace" />;
  }

  return children;
}

function PublicOnly({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) {
    return <LoadingScreen />;
  }
  return isAuthenticated ? <Navigate replace to="/dashboard" /> : children;
}

function LoginRoute() {
  const navigate = useNavigate();
  return <Login onHome={() => navigate("/")} onSwitch={() => navigate("/register")} />;
}

function RegisterRoute() {
  const navigate = useNavigate();
  return <Register onHome={() => navigate("/")} onSwitch={() => navigate("/login")} />;
}

function AppRoutes() {
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    document.body.classList.toggle("dark", darkMode);
  }, [darkMode]);

  return (
    <>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/marketplace" element={<Marketplace />} />
        <Route path="/marketplace/product/:id" element={<ProductDetails />} />
        <Route path="/login" element={<PublicOnly><main className="authPage"><LoginRoute /></main></PublicOnly>} />
        <Route path="/register" element={<PublicOnly><main className="authPage"><RegisterRoute /></main></PublicOnly>} />
        <Route path="/forgot-password" element={<PublicOnly><main className="authPage"><ForgotPasswordPage /></main></PublicOnly>} />
        <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/cart" element={<Cart />} />
          <Route path="/checkout" element={<Checkout />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/wishlist" element={<WishlistPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage darkMode={darkMode} onToggleTheme={() => setDarkMode((value) => !value)} />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/payment/success" element={<PaymentStatus success />} />
          <Route path="/payment/failed" element={<PaymentStatus success={false} />} />
          <Route path="/sell" element={<ProtectedRoute sellerOnly><SellProductsPage /></ProtectedRoute>} />
          <Route path="/seller" element={<ProtectedRoute sellerOnly><SellerDashboard /></ProtectedRoute>} />
          <Route path="/admin" element={<ProtectedRoute adminOnly><AdminDashboard /></ProtectedRoute>} />
        </Route>
      </Routes>
      <Toaster position="top-right" toastOptions={{ className: "toast" }} />
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <AuthProvider>
          <CartProvider>
            <AppRoutes />
          </CartProvider>
        </AuthProvider>
      </ErrorBoundary>
    </BrowserRouter>
  );
}
