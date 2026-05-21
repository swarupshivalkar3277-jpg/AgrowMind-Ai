import { useEffect, useState } from "react";

import { AuthProvider, useAuth } from "./context/AuthContext";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Register from "./pages/Register";
import { API_BASE } from "./services/authService";

import "./App.css";

function ProtectedApp() {
  const { isAuthenticated, loading } = useAuth();
  const [view, setView] = useState("home");
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    document.body.classList.toggle("dark", darkMode);
  }, [darkMode]);

  useEffect(() => {
    if (isAuthenticated) {
      setView("dashboard");
    }
  }, [isAuthenticated]);

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

  if (isAuthenticated && view === "dashboard") {
    return (
      <>
        <div className="floatingThemeButton">
          <button
            aria-label="Toggle theme"
            className="themeToggle"
            onClick={() => setDarkMode((current) => !current)}
            type="button"
          >
            {darkMode ? "Light" : "Dark"}
          </button>
        </div>
        <Dashboard onHome={() => setView("home")} />
      </>
    );
  }

  if (view === "home") {
    return (
      <div className="homePage">
        <nav className="siteNav">
          <button className="brandButton" onClick={() => setView("home")} type="button">
            AgroMind AI
          </button>
          <div className="navActions">
            <button className="secondaryButton" onClick={() => setView("login")} type="button">
              Login
            </button>
            <button className="primaryButton" onClick={() => setView("register")} type="button">
              Register
            </button>
            <button
              aria-label="Toggle theme"
              className="themeToggle"
              onClick={() => setDarkMode((current) => !current)}
              type="button"
            >
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
                Upload crop leaf images, detect diseases instantly, and manage
                predictions securely using your AgroMind AI account.
              </p>
              <div className="heroActions">
                <button className="primaryButton" onClick={() => setView("register")} type="button">
                  Create Account
                </button>
                <button className="secondaryButton" onClick={() => setView("login")} type="button">
                  Login
                </button>
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
            <p>
              AI-powered disease prediction for tomato, mango, and coconut crops
              using secure JWT authentication.
            </p>
          </article>
          <article className="featureCard">
            <h2>Saved Prediction History</h2>
            <p>
              Every authenticated crop prediction is automatically stored in your
              dashboard for future review and monitoring.
            </p>
          </article>
          <article className="featureCard">
            <h2>Multi-Role Platform</h2>
            <p>
              Supports users, farmers, buyers, and admin workflows for scalable
              agricultural ecosystems.
            </p>
          </article>
        </section>
      </div>
    );
  }

  return (
    <main className="authPage">
      <div className="floatingThemeButton">
        <button
          aria-label="Toggle theme"
          className="themeToggle"
          onClick={() => setDarkMode((current) => !current)}
          type="button"
        >
          {darkMode ? "Light" : "Dark"}
        </button>
      </div>
      {view === "login" ? (
        <Login onHome={() => setView("home")} onSwitch={() => setView("register")} />
      ) : (
        <Register onHome={() => setView("home")} onSwitch={() => setView("login")} />
      )}
    </main>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ProtectedApp />
    </AuthProvider>
  );
}
