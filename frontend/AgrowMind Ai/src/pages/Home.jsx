import { API_BASE } from "../services/authService";

const features = [
  {
    title: "Secure crop analysis",
    text: "JWT-protected prediction tools for tomato, mango, and coconut leaf images.",
  },
  {
    title: "Saved history",
    text: "Every authenticated prediction is stored with your account for quick review.",
  },
  {
    title: "Role-ready access",
    text: "Accounts support user, farmer, buyer, and admin roles for future workflows.",
  },
];

export default function Home({ isAuthenticated, onDashboard, onLogin, onRegister }) {
  return (
    <main className="homePage">
      <nav className="siteNav" aria-label="Primary navigation">
        <button className="brandButton" onClick={onDashboard} type="button">
          AgroMind AI
        </button>
        <div className="navActions">
          {isAuthenticated ? (
            <button className="secondaryButton" onClick={onDashboard} type="button">
              Dashboard
            </button>
          ) : (
            <>
              <button className="secondaryButton" onClick={onLogin} type="button">
                Login
              </button>
              <button onClick={onRegister} type="button">
                Register
              </button>
            </>
          )}
        </div>
      </nav>

      <section className="homeHero">
        <div className="heroCopy">
          <p className="eyebrow">AI crop health assistant</p>
          <h1>AgroMind AI</h1>
          <p>
            Upload a crop leaf image, get disease predictions, and keep every result tied to a
            secure account.
          </p>
          <div className="heroActions">
            <button onClick={isAuthenticated ? onDashboard : onRegister} type="button">
              {isAuthenticated ? "Open Dashboard" : "Create Account"}
            </button>
            <button className="secondaryButton" onClick={isAuthenticated ? onDashboard : onLogin} type="button">
              {isAuthenticated ? "View History" : "Login"}
            </button>
          </div>
          <span className="apiStatus">API: {API_BASE}</span>
        </div>
      </section>

      <section className="featureBand" aria-label="AgroMind features">
        {features.map((feature) => (
          <article className="featureCard" key={feature.title}>
            <h2>{feature.title}</h2>
            <p>{feature.text}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
