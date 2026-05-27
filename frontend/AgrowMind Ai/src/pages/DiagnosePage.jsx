import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { BadgeCheck, Camera, ImagePlus, ShieldCheck, Sparkles } from "lucide-react";
import toast from "react-hot-toast";

import PredictionResultCard from "../components/PredictionResultCard";
import UploadBox from "../components/UploadBox";
import { useAuth } from "../context/AuthContext";
import api, { getHistory, PREDICTION_TIMEOUT_MS } from "../services/authService";
import { compressImage } from "../utils/imageCompression";
import { downloadPredictionReport } from "../utils/reportPdf";

const crops = [
  { value: "tomato", label: "Tomato" },
  { value: "mango", label: "Mango" },
  { value: "coconut", label: "Coconut" },
];

const predictionSteps = [
  "Uploading image",
  "Preparing AI model",
  "Analyzing crop",
  "Detecting disease",
  "Generating treatment",
];

function normalizeError(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.message) return detail.message;
  if (detail?.reason && detail?.reason !== detail?.error) return `${detail.error || "Prediction failed"}: ${detail.reason}`;
  if (detail?.error) return detail.error;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join(", ");
  return error?.message || "Prediction failed";
}

export default function DiagnosePage() {
  const { user } = useAuth();
  const [crop, setCrop] = useState("tomato");
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [progressStep, setProgressStep] = useState(0);
  const [recentDiagnoses, setRecentDiagnoses] = useState([]);

  useEffect(() => () => previewUrl && URL.revokeObjectURL(previewUrl), [previewUrl]);

  useEffect(() => {
    getHistory().then(({ data }) => setRecentDiagnoses((data.items || []).slice(0, 4))).catch(() => null);
  }, []);

  useEffect(() => {
    if (!loading) return undefined;
    setProgressStep(0);
    const timer = window.setInterval(() => {
      setProgressStep((step) => Math.min(step + 1, predictionSteps.length - 1));
    }, 1100);
    return () => window.clearInterval(timer);
  }, [loading]);

  async function handleFileChange(event) {
    const selected = event.target.files?.[0];
    if (!selected) return;
    if (!selected.type.startsWith("image/")) {
      setError("Please upload a valid image file.");
      return;
    }
    const compressed = await compressImage(selected);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(compressed);
    setPreviewUrl(URL.createObjectURL(compressed));
    setResult(null);
    setError("");
  }

  async function handlePredict(event) {
    event.preventDefault();
    if (!file) {
      setError("Please upload or capture a crop leaf image.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    setLoading(true);
    setError("");

    try {
      const { data } = await api.post(`/predict/${crop}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: PREDICTION_TIMEOUT_MS,
      });
      setResult({ ...data, created_at: new Date().toISOString() });
      getHistory().catch(() => null);
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
      <motion.section className="pageHero compactHero flagshipHero" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <div>
          <span className="eyebrowText">AI Disease Detection</span>
          <h1>Diagnose crop health from a single leaf image.</h1>
          <p>Upload from gallery or camera, watch the scan progress, then get treatment, prevention, severity, and matched marketplace inputs.</p>
          <div className="heroMeta">
            <span><ImagePlus size={17} /> Gallery upload</span>
            <span><Camera size={17} /> Camera capture</span>
            <span><Sparkles size={17} /> AI recommendations</span>
          </div>
          <div className="trustBadgeRow">
            <span><BadgeCheck size={16} /> AI verified predictions</span>
            <span><ShieldCheck size={16} /> Private crop images</span>
          </div>
        </div>
      </motion.section>

      <section className="diagnoseGrid">
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
            <div className="analysisLoader premiumLoader">
              <div className="predictionProgress">
                {predictionSteps.map((step, index) => <span className={index <= progressStep ? "active" : ""} key={step}>{step}</span>)}
              </div>
              <strong>{predictionSteps[progressStep]}...</strong>
              <p>Optimized upload, lazy model loading, disease classification, and treatment generation are running.</p>
            </div>
          ) : (
            <PredictionResultCard
              crop={result?.crop || crop}
              onDownload={() => downloadPredictionReport({ user, crop: result.crop, prediction: result.prediction, createdAt: result.created_at })}
              prediction={result?.prediction}
            />
          )}
        </div>
      </section>
      <section className="panel recentDiagnoses">
        <div className="sectionHeader"><div><span className="eyebrowText">Recently Diagnosed</span><h2>Disease history</h2></div></div>
        <div className="diagnosisChipGrid">
          {recentDiagnoses.map((item) => <span key={item.id}>{item.crop}: {item.prediction?.disease?.replaceAll("_", " ") || "Scan"}</span>)}
          {recentDiagnoses.length === 0 && <span>Run your first scan to build a crop health timeline.</span>}
        </div>
      </section>
    </main>
  );
}
