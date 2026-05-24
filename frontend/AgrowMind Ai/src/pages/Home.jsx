import { Link } from "react-router-dom";
import { BrainCircuit, CloudSun, Leaf, ScanSearch, ShoppingBag, ShieldCheck, Star, Truck } from "lucide-react";

import PublicNav from "../components/PublicNav";
import { useAuth } from "../context/AuthContext";

const features = [
  {
    icon: ScanSearch,
    title: "AI crop disease detection",
    text: "Upload tomato, mango, or coconut leaf images and receive disease insights with confidence, treatment guidance, and prevention steps.",
  },
  {
    icon: ShoppingBag,
    title: "Smart farm marketplace",
    text: "Browse fertilizers, seeds, pesticides, tools, and saplings connected to crop needs and disease recommendations.",
  },
  {
    icon: ShieldCheck,
    title: "Secure farmer accounts",
    text: "OTP, Google sign-in, JWT validation, saved reports, order tracking, and admin-only operations keep workflows protected.",
  },
];

export default function Home() {
  const { isAuthenticated } = useAuth();

  return (
    <main className="homePage">
      <PublicNav />

      <section className="homeHero">
        <div className="heroCopy">
          <p className="eyebrow">AI agriculture assistant</p>
          <h1>AgroMind AI</h1>
          <p>
            Detect crop disease early, understand treatment options, and discover relevant farm
            inputs from one production-ready agriculture platform.
          </p>
          <div className="heroActions">
            <Link className="primaryButton" to={isAuthenticated ? "/dashboard" : "/register"}>
              {isAuthenticated ? "Open Dashboard" : "Start Free"}
            </Link>
            <Link className="secondaryButton" to="/marketplace">
              Browse Marketplace
            </Link>
          </div>
        </div>
      </section>

      <section className="featureBand" aria-label="AgroMind features">
        {features.map((feature) => {
          const Icon = feature.icon;
          return (
            <article className="featureCard" key={feature.title}>
              <Icon size={26} />
              <h2>{feature.title}</h2>
              <p>{feature.text}</p>
            </article>
          );
        })}
      </section>

      <section className="diseaseIntro">
        <div>
          <span className="eyebrowText">Disease intelligence</span>
          <h2>From leaf image to practical field action.</h2>
          <p>
            AgroMind AI turns crop photos into understandable disease predictions, severity
            context, organic solutions, irrigation advice, and marketplace recommendations.
          </p>
        </div>
        <div className="diseaseSteps">
          <span><Leaf size={18} /> Select crop</span>
          <span><BrainCircuit size={18} /> Run AI scan</span>
          <span><Truck size={18} /> Buy recommended inputs</span>
        </div>
      </section>

      <section className="marketPreview">
        <div>
          <span className="eyebrowText">Marketplace preview</span>
          <h2>Visitors can browse first, then login when ready to buy.</h2>
          <p>
            Product listings and details are open to everyone. Cart, checkout, orders, wishlist,
            and buy-now actions are reserved for authenticated users.
          </p>
        </div>
        <Link className="primaryButton" to="/marketplace">Explore Products</Link>
      </section>

      <section className="featureBand" aria-label="Platform statistics">
        {[
          ["3 crops", "Tomato, mango, and coconut disease intelligence."],
          ["Secure payments", "Razorpay checkout with stock reduction after verification."],
          ["Admin ops", "Users, products, orders, analytics, and reports."],
        ].map(([title, text]) => <article className="featureCard statFeature" key={title}><Star size={24} /><h2>{title}</h2><p>{text}</p></article>)}
      </section>

      <section className="diseaseIntro">
        <div>
          <span className="eyebrowText">Weather intelligence</span>
          <h2>Field decisions that adapt to changing conditions.</h2>
          <p>Humidity, rain probability, wind, temperature, and warnings help farmers time treatments and reduce disease spread.</p>
        </div>
        <div className="diseaseSteps">
          <span><CloudSun size={18} /> 7-day forecast</span>
          <span><Leaf size={18} /> Crop advisory</span>
          <span><ShieldCheck size={18} /> Risk warnings</span>
        </div>
      </section>

      <section className="marketPreview">
        <div>
          <span className="eyebrowText">FAQ</span>
          <h2>Built for real farmer workflows, not demos.</h2>
          <p>Farmers can diagnose, review history, buy products, track orders, export reports, and ask the assistant within a few taps.</p>
        </div>
        <Link className="primaryButton" to={isAuthenticated ? "/diagnose" : "/register"}>Try Disease Detection</Link>
      </section>

      <footer className="siteFooter">
        <strong>AgroMind AI</strong>
        <span>Crop health, farm inputs, and secure commerce for modern agriculture.</span>
      </footer>
    </main>
  );
}
