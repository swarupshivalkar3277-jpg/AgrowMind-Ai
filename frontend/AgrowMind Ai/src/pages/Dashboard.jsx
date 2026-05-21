import { useEffect, useState } from "react";

import { useAuth } from "../context/AuthContext";
import api, { API_BASE, getHistory } from "../services/authService";

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
      setResult(data);
      await refreshHistory();
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="dashboard">
      <header className="topbar">
        <div>
          <p className="eyebrow">Protected Dashboard</p>
          <h1>AgroMind AI</h1>
          <span>{user?.name} - {user?.role}</span>
        </div>
        <div className="topbarActions">
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
          {result ? (
            <>
              <p className="eyebrow">AI Prediction</p>
              <h2>{formatDiseaseName(result.prediction?.disease)}</h2>
              <div className="metricGrid">
                <article>
                  <span>Confidence</span>
                  <strong>{result.prediction?.confidence}%</strong>
                </article>
                <article>
                  <span>Crop</span>
                  <strong>{result.crop}</strong>
                </article>
              </div>
            </>
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
          <h2>Prediction History</h2>
          <span>{history.length} saved</span>
        </div>
        <div className="historyList">
          {history.map((item) => (
            <article key={item.id}>
              <div>
                <strong>{formatDiseaseName(item.prediction?.disease)}</strong>
                <span>{item.crop}</span>
              </div>
              <small>{new Date(item.created_at).toLocaleString()}</small>
            </article>
          ))}
          {history.length === 0 && <p>No predictions yet.</p>}
        </div>
      </section>
    </main>
  );
}
