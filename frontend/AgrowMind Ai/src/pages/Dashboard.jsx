import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import PredictionCards, { SeverityBadge } from "../components/PredictionCards";
import api, { API_BASE, getHistory } from "../services/authService";
import { downloadPredictionReport } from "../utils/reportPdf";

const crops = [
  { value: "tomato", label: "Tomato" },
  { value: "mango", label: "Mango" },
  { value: "coconut", label: "Coconut" },
];

function normalizeError(error) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (detail?.error) {
    return detail.error;
  }

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).filter(Boolean).join(", ");
  }

  return error?.message || "Request failed";
}

function formatDiseaseName(value = "") {
  return value.replaceAll("_", " ");
}

export default function Dashboard({ onHome }) {
  const { logout, user } = useAuth();
  const [crop, setCrop] = useState("tomato");
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [historyFilter, setHistoryFilter] = useState("");

  useEffect(() => {
    refreshHistory();
  }, []);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  async function refreshHistory() {
    try {
      const { data } = await getHistory();
      setHistory(data.items || []);
    } catch {
      setHistory([]);
    }
  }

  function handleFileChange(event) {
    const selected = event.target.files?.[0];

    if (!selected) {
      return;
    }

    if (!selected.type.startsWith("image/")) {
      setError("Please upload a valid image file.");
      return;
    }

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    setFile(selected);
    setPreviewUrl(URL.createObjectURL(selected));
    setResult(null);
    setError("");
  }

  async function handlePredict(event) {
    event.preventDefault();

    if (!file) {
      setError("Please upload a crop leaf image.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    setError("");

    try {
      const { data } = await api.post(`/predict/${crop}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult({ ...data, created_at: new Date().toISOString() });
      await refreshHistory();
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoading(false);
    }
  }

  const filteredHistory = history.filter((item) => {
    const query = historyFilter.trim().toLowerCase();

    if (!query) {
      return true;
    }

    return [
      item.crop,
      item.prediction?.disease,
      item.prediction?.severity,
      item.prediction?.harvest_risk,
    ]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query));
  });

  return (
    <main className="dashboard">
      <header className="topbar">
        <div>
          <p className="eyebrow">Protected Dashboard</p>
          <h1>AgroMind AI</h1>
          <span>{user?.name} - {user?.role}</span>
        </div>
        <div className="topbarActions">
          <Link className="secondaryButton" to="/marketplace">
            Marketplace
          </Link>
          {(user?.role === "farmer" || user?.role === "seller" || user?.role === "admin") && (
            <Link className="secondaryButton" to="/sell">
              Sell Products
            </Link>
          )}
          <button className="secondaryButton" onClick={onHome} type="button">
            Home
          </button>
          <button className="secondaryButton" onClick={logout} type="button">
            Logout
          </button>
        </div>
      </header>

      <section className="workspace">
        <form className="panel controls" onSubmit={handlePredict}>
          <label>
            <span>Select Crop</span>
            <select onChange={(event) => setCrop(event.target.value)} value={crop}>
              {crops.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Leaf Image</span>
            <input accept="image/*" onChange={handleFileChange} type="file" />
          </label>
          {previewUrl && <img alt="Leaf preview" className="previewImage" src={previewUrl} />}
          {error && <div className="alert">{error}</div>}
          <button disabled={loading} type="submit">
            {loading ? "Analyzing..." : "Predict Disease"}
          </button>
          <div className="apiStatus">API: {API_BASE}</div>
        </form>

        <section className="panel resultPanel">
          {loading ? (
            <div className="analysisLoader">
              <span />
              <strong>Analyzing crop health...</strong>
              <p>Running disease detection and preparing farming advice.</p>
            </div>
          ) : result ? (
            <PredictionCards
              crop={result.crop}
              onDownload={() =>
                downloadPredictionReport({
                  user,
                  crop: result.crop,
                  prediction: result.prediction,
                  createdAt: result.created_at,
                })
              }
              prediction={result.prediction}
            />
          ) : (
            <div className="emptyState">
              <h2>Ready for analysis</h2>
              <p>Upload a crop leaf image to call the protected prediction API.</p>
            </div>
          )}
        </section>
      </section>

      <section className="panel history">
        <div className="sectionHeader">
          <div>
            <h2>Prediction History</h2>
            <span>{filteredHistory.length} of {history.length} saved</span>
          </div>
          <label className="historySearch">
            <span>Search history</span>
            <input
              onChange={(event) => setHistoryFilter(event.target.value)}
              placeholder="Filter by crop, disease, severity"
              type="search"
              value={historyFilter}
            />
          </label>
        </div>
        <div className="historyList">
          {filteredHistory.map((item) => (
            <article key={item.id}>
              <div>
                <strong>{formatDiseaseName(item.prediction?.disease)}</strong>
                <span>{item.crop} - {item.prediction?.confidence}% confidence</span>
              </div>
              <SeverityBadge value={item.prediction?.severity} />
              <small>{new Date(item.created_at).toLocaleString()}</small>
            </article>
          ))}
          {history.length === 0 && <p>No predictions yet.</p>}
          {history.length > 0 && filteredHistory.length === 0 && <p>No matching predictions.</p>}
        </div>
      </section>
    </main>
  );
}
