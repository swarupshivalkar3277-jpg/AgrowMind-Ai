import { lazy, Suspense, useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";

import AppShell from "./components/AppShell";
import ErrorBoundary from "./components/ErrorBoundary";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { CartProvider } from "./context/CartContext";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";

const AdminDashboard = lazy(() => import("./pages/AdminDashboard"));
const AdminAnalytics = lazy(() => import("./pages/admin/AdminAnalytics"));
const AdminOrders = lazy(() => import("./pages/admin/AdminOrders"));
const AdminPredictions = lazy(() => import("./pages/admin/AdminPredictions"));
const AdminProductForm = lazy(() => import("./pages/admin/AdminProductForm"));
const AdminProducts = lazy(() => import("./pages/admin/AdminProducts"));
const AdminReports = lazy(() => import("./pages/admin/AdminReports"));
const AdminSettings = lazy(() => import("./pages/admin/AdminSettings"));
const AdminUsers = lazy(() => import("./pages/admin/AdminUsers"));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const AssistantPage = lazy(() => import("./pages/AssistantPage"));
const Cart = lazy(() => import("./pages/Cart"));
const Checkout = lazy(() => import("./pages/Checkout"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const DiagnosePage = lazy(() => import("./pages/DiagnosePage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const Marketplace = lazy(() => import("./pages/Marketplace"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage"));
const Orders = lazy(() => import("./pages/Orders"));
const PaymentStatus = lazy(() => import("./pages/PaymentStatus"));
const ProductDetails = lazy(() => import("./pages/ProductDetails"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const WeatherPage = lazy(() => import("./pages/WeatherPage"));
const WishlistPage = lazy(() => import("./pages/WishlistPage"));

function LoadingScreen({ label = "Loading secure workspace..." }) {
  return (
    <main className="stateScreen premiumLoader">
      <div className="skeletonStack" aria-hidden="true">
        <i />
        <i />
        <i />
      </div>
      <h1>AgroMind AI</h1>
      <p>{label}</p>
    </main>
  );
}

function LazyPage({ children }) {
  return <Suspense fallback={<LoadingScreen label="Preparing your workspace..." />}>{children}</Suspense>;
}

function ProtectedRoute({ children, adminOnly = false }) {
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
        <Route path="/marketplace" element={<LazyPage><Marketplace /></LazyPage>} />
        <Route path="/marketplace/product/:id" element={<LazyPage><ProductDetails /></LazyPage>} />
        <Route path="/login" element={<PublicOnly><main className="authPage"><LoginRoute /></main></PublicOnly>} />
        <Route path="/register" element={<PublicOnly><main className="authPage"><RegisterRoute /></main></PublicOnly>} />
        <Route path="/forgot-password" element={<PublicOnly><main className="authPage"><ForgotPasswordPage /></main></PublicOnly>} />
        <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
          <Route path="/dashboard" element={<LazyPage><Dashboard /></LazyPage>} />
          <Route path="/diagnose" element={<LazyPage><DiagnosePage /></LazyPage>} />
          <Route path="/cart" element={<LazyPage><Cart /></LazyPage>} />
          <Route path="/checkout" element={<LazyPage><Checkout /></LazyPage>} />
          <Route path="/orders" element={<LazyPage><Orders /></LazyPage>} />
          <Route path="/wishlist" element={<LazyPage><WishlistPage /></LazyPage>} />
          <Route path="/history" element={<LazyPage><HistoryPage /></LazyPage>} />
          <Route path="/analytics" element={<LazyPage><AnalyticsPage /></LazyPage>} />
          <Route path="/weather" element={<LazyPage><WeatherPage /></LazyPage>} />
          <Route path="/assistant" element={<LazyPage><AssistantPage /></LazyPage>} />
          <Route path="/reports" element={<LazyPage><ReportsPage /></LazyPage>} />
          <Route path="/settings" element={<LazyPage><SettingsPage darkMode={darkMode} onToggleTheme={() => setDarkMode((value) => !value)} /></LazyPage>} />
          <Route path="/notifications" element={<LazyPage><NotificationsPage /></LazyPage>} />
          <Route path="/payment/success" element={<LazyPage><PaymentStatus success /></LazyPage>} />
          <Route path="/payment/failed" element={<LazyPage><PaymentStatus success={false} /></LazyPage>} />
          <Route path="/admin" element={<Navigate replace to="/admin/dashboard" />} />
          <Route path="/admin/dashboard" element={<ProtectedRoute adminOnly><LazyPage><AdminDashboard /></LazyPage></ProtectedRoute>} />
          <Route path="/admin/users" element={<ProtectedRoute adminOnly><LazyPage><AdminUsers /></LazyPage></ProtectedRoute>} />
          <Route path="/admin/products" element={<ProtectedRoute adminOnly><LazyPage><AdminProducts /></LazyPage></ProtectedRoute>} />
          <Route path="/admin/products/add" element={<ProtectedRoute adminOnly><LazyPage><AdminProductForm /></LazyPage></ProtectedRoute>} />
          <Route path="/admin/products/edit/:id" element={<ProtectedRoute adminOnly><LazyPage><AdminProductForm /></LazyPage></ProtectedRoute>} />
          <Route path="/admin/orders" element={<ProtectedRoute adminOnly><LazyPage><AdminOrders /></LazyPage></ProtectedRoute>} />
          <Route path="/admin/predictions" element={<ProtectedRoute adminOnly><LazyPage><AdminPredictions /></LazyPage></ProtectedRoute>} />
          <Route path="/admin/analytics" element={<ProtectedRoute adminOnly><LazyPage><AdminAnalytics /></LazyPage></ProtectedRoute>} />
          <Route path="/admin/reports" element={<ProtectedRoute adminOnly><LazyPage><AdminReports /></LazyPage></ProtectedRoute>} />
          <Route path="/admin/settings" element={<ProtectedRoute adminOnly><LazyPage><AdminSettings /></LazyPage></ProtectedRoute>} />
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
