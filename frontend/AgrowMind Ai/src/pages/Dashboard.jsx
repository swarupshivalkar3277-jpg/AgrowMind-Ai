import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { CalendarClock, Quote, UserRound } from "lucide-react";
import toast from "react-hot-toast";

import AIChatAssistantPlaceholder from "../components/AIChatAssistantPlaceholder";
import AnalyticsCard from "../components/AnalyticsCard";
import DashboardStats from "../components/DashboardStats";
import PredictionResultCard from "../components/PredictionResultCard";
import UploadBox from "../components/UploadBox";
import WeatherCard from "../components/WeatherCard";
import { useAuth } from "../context/AuthContext";
import api, { getHistory } from "../services/authService";
import { downloadPredictionReport } from "../utils/reportPdf";

const crops = [
  { value: "tomato", label: "Tomato" },
  { value: "mango", label: "Mango" },
  { value: "coconut", label: "Coconut" },
];

function normalizeError(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.error) return detail.error;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join(", ");
  return error?.message || "Request failed";
}

export default function Dashboard() {
  const { user } = useAuth();
  const [crop, setCrop] = useState("tomato");
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const now = useMemo(() => new Date(), []);

  useEffect(() => {
    getHistory().then(({ data }) => setHistory(data.items || [])).catch(() => setHistory([]));
  }, []);

  useEffect(() => () => previewUrl && URL.revokeObjectURL(previewUrl), [previewUrl]);

  function handleFileChange(event) {
    const selected = event.target.files?.[0];
    if (!selected) return;
    if (!selected.type.startsWith("image/")) {
      setError("Please upload a valid image file.");
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
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
      const historyResult = await getHistory();
      setHistory(historyResult.data.items || []);
      toast.success("Prediction completed");
    } catch (err) {
      const message = normalizeError(err);
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="pageStack">
      <motion.section className="dashboardHero" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}>
        <div>
          <span className="eyebrowText">AI Agriculture SaaS</span>
          <h1>Welcome back, {user?.name || "farmer"}</h1>
          <p>Detect crop disease, convert insight into treatment, and buy trusted farm inputs from one workspace.</p>
          <div className="heroMeta">
            <span><CalendarClock size={17} /> {now.toLocaleDateString()} {now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
            <span><Quote size={17} /> Healthy crops begin with early signals.</span>
          </div>
        </div>
        <article className="profileSummary">
          <UserRound size={28} />
          <strong>{user?.name}</strong>
          <span>{user?.role || "user"} account</span>
          <small>{user?.email}</small>
        </article>
      </motion.section>

      <DashboardStats historyCount={history.length} />

      <section className="dashboardGrid">
        <UploadBox
          crop={crop}
          crops={crops}
          error={error}
          file={file}
          loading={loading}
          onCrop={setCrop}
          onFile={handleFileChange}
          onSubmit={handlePredict}
          previewUrl={previewUrl}
        />
        <div className="predictionPanel">
          {loading ? (
            <div className="analysisLoader"><span /><strong>Analyzing crop health...</strong><p>Preparing disease intelligence and product matches.</p></div>
          ) : (
            <PredictionResultCard
              crop={result?.crop || crop}
              onDownload={() => downloadPredictionReport({ user, crop: result.crop, prediction: result.prediction, createdAt: result.created_at })}
              prediction={result?.prediction}
            />
          )}
        </div>
      </section>

      <section className="insightGrid">
        <WeatherCard />
        <AnalyticsCard />
        <AIChatAssistantPlaceholder />
      </section>
    </main>
  );
}
