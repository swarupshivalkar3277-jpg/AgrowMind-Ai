import { useEffect, useState } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";

import { AuthProvider, useAuth } from "./context/AuthContext";
import { CartProvider } from "./context/CartContext";
import CartDrawer from "./components/CartDrawer";
import MarketplaceNav from "./components/MarketplaceNav";
import AdminDashboard from "./pages/AdminDashboard";
import Cart from "./pages/Cart";
import Checkout from "./pages/Checkout";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Marketplace from "./pages/Marketplace";
import Orders from "./pages/Orders";
import PaymentStatus from "./pages/PaymentStatus";
import ProductDetails from "./pages/ProductDetails";
import Register from "./pages/Register";
import SellerDashboard from "./pages/SellerDashboard";
import { API_BASE } from "./services/authService";

import "./App.css";

function ProtectedRoute({ children, adminOnly = false }) {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) {
    return <div className="loadingScreen"><div className="analysisLoader"><span /><strong>Loading secure workspace...</strong></div></div>;
  }

  if (!isAuthenticated) {
    return <Navigate replace to="/login" />;
  }

  if (adminOnly && user?.role !== "admin") {
    return <Navigate replace to="/dashboard" />;
  }

  return children;
}

function SellerRoute({ children }) {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) {
    return <div className="loadingScreen"><div className="analysisLoader"><span /><strong>Loading seller tools...</strong></div></div>;
  }

  if (!isAuthenticated) {
    return <Navigate replace to="/login" />;
  }

  if (!["admin", "farmer", "seller"].includes(user?.role)) {
    return <Navigate replace to="/marketplace" />;
  }

  return children;
}

function HomePage({ darkMode, onToggleTheme }) {
  return (
    <div className="homePage">
      <nav className="siteNav">
        <Link className="brandButton" to="/">AgroMind AI</Link>
        <div className="navActions">
          <Link className="secondaryButton" to="/marketplace">Marketplace</Link>
          <Link className="secondaryButton" to="/login">Login</Link>
          <Link className="primaryButton" to="/register">Register</Link>
          <button aria-label="Toggle theme" className="themeToggle" onClick={onToggleTheme} type="button">
            {darkMode ? "Light" : "Dark"}
          </button>
        </div>
      </nav>

      <section className="homeHero">
        <div className="heroGlass">
          <div className="heroCopy">
            <p className="eyebrow">AI Crop Health Assistant</p>
            <h1>
              Smart Farming <br />
              <span className="heroGradient">Powered by AI</span>
            </h1>
            <p>
              Detect crop diseases, receive treatment guidance, and shop matched
              agriculture products from one secure AgroMind AI workspace.
            </p>
            <div className="heroActions">
              <Link className="primaryButton" to="/register">Create Account</Link>
              <Link className="secondaryButton" to="/marketplace">Open Marketplace</Link>
            </div>
            <div className="apiStatus">
              API Connected: <strong>{API_BASE}</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="featureBand">
        <article className="featureCard">
          <h2>Secure Crop Analysis</h2>
          <p>AI-powered prediction for tomato, mango, and coconut with saved history.</p>
        </article>
        <article className="featureCard">
          <h2>Smart Marketplace</h2>
          <p>Recommended fertilizers, pesticides, seeds, trees, and organic products.</p>
        </article>
        <article className="featureCard">
          <h2>Orders and Cart</h2>
          <p>Persistent cart, checkout, payment records, and delivery tracking.</p>
        </article>
      </section>
    </div>
  );
}

function LoginRoute() {
  const navigate = useNavigate();
  return <Login onHome={() => navigate("/")} onSwitch={() => navigate("/register")} />;
}

function RegisterRoute() {
  const navigate = useNavigate();
  return <Register onHome={() => navigate("/")} onSwitch={() => navigate("/login")} />;
}

function DashboardRoute() {
  const navigate = useNavigate();
  return <Dashboard onHome={() => navigate("/")} />;
}

function AppRoutes() {
  const { isAuthenticated, loading } = useAuth();
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    document.body.classList.toggle("dark", darkMode);
  }, [darkMode]);

  if (loading) {
    return (
      <div className="loadingScreen">
        <div className="heroGlass">
          <div className="heroCopy">
            <p className="eyebrow">AI Agricultural Intelligence</p>
            <h1>
              AgroMind <br />
              <span className="heroGradient">AI</span>
            </h1>
            <p>Loading secure AI workspace...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <Routes>
        <Route path="/" element={isAuthenticated ? <Navigate to="/dashboard" /> : <HomePage darkMode={darkMode} onToggleTheme={() => setDarkMode((current) => !current)} />} />
        <Route path="/login" element={<main className="authPage"><LoginRoute /></main>} />
        <Route path="/register" element={<main className="authPage"><RegisterRoute /></main>} />
        <Route path="/dashboard" element={<ProtectedRoute><div className="floatingThemeButton"><button aria-label="Toggle theme" className="themeToggle" onClick={() => setDarkMode((current) => !current)} type="button">{darkMode ? "Light" : "Dark"}</button></div><DashboardRoute /></ProtectedRoute>} />
        <Route path="/marketplace" element={<><MarketplaceNav darkMode={darkMode} onToggleTheme={() => setDarkMode((current) => !current)} /><Marketplace /></>} />
        <Route path="/marketplace/product/:id" element={<><MarketplaceNav darkMode={darkMode} onToggleTheme={() => setDarkMode((current) => !current)} /><ProductDetails /></>} />
        <Route path="/cart" element={<ProtectedRoute><MarketplaceNav darkMode={darkMode} onToggleTheme={() => setDarkMode((current) => !current)} /><Cart /></ProtectedRoute>} />
        <Route path="/checkout" element={<ProtectedRoute><MarketplaceNav darkMode={darkMode} onToggleTheme={() => setDarkMode((current) => !current)} /><Checkout /></ProtectedRoute>} />
        <Route path="/orders" element={<ProtectedRoute><MarketplaceNav darkMode={darkMode} onToggleTheme={() => setDarkMode((current) => !current)} /><Orders /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute adminOnly><MarketplaceNav darkMode={darkMode} onToggleTheme={() => setDarkMode((current) => !current)} /><AdminDashboard /></ProtectedRoute>} />
        <Route path="/sell" element={<SellerRoute><MarketplaceNav darkMode={darkMode} onToggleTheme={() => setDarkMode((current) => !current)} /><SellerDashboard /></SellerRoute>} />
        <Route path="/payment/success" element={<ProtectedRoute><MarketplaceNav darkMode={darkMode} onToggleTheme={() => setDarkMode((current) => !current)} /><PaymentStatus success /></ProtectedRoute>} />
        <Route path="/payment/failed" element={<ProtectedRoute><MarketplaceNav darkMode={darkMode} onToggleTheme={() => setDarkMode((current) => !current)} /><PaymentStatus success={false} /></ProtectedRoute>} />
      </Routes>
      <CartDrawer />
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <CartProvider>
          <AppRoutes />
        </CartProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
