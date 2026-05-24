import { useEffect, useMemo, useState } from "react";

import HistoryCard from "../components/HistoryCard";
import { useAuth } from "../context/AuthContext";
import { getHistory } from "../services/authService";
import { downloadPredictionReport } from "../utils/reportPdf";

export default function HistoryPage() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState("");
  const [crop, setCrop] = useState("");
  const [severity, setSeverity] = useState("");
  const [view, setView] = useState("cards");

  useEffect(() => {
    getHistory().then(({ data }) => setItems(data.items || [])).catch(() => setItems([]));
  }, []);

  const filtered = useMemo(() => {
    return items.filter((item) => {
      const text = `${item.crop} ${item.prediction?.disease} ${item.prediction?.harvest_risk}`.toLowerCase();
      const matchesQuery = !query || text.includes(query.toLowerCase());
      const matchesSeverity = !severity || item.prediction?.severity === severity;
      const matchesCrop = !crop || item.crop === crop;
      return matchesQuery && matchesSeverity && matchesCrop;
    });
  }, [crop, items, query, severity]);

  function exportCsv() {
    const rows = [["Crop", "Disease", "Confidence", "Severity", "Created At"], ...filtered.map((item) => [item.crop, item.prediction?.disease, item.prediction?.confidence, item.prediction?.severity, item.created_at])];
    const csv = rows.map((row) => row.map((cell) => `"${String(cell || "").replaceAll('"', '""')}"`).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "agromind-prediction-history.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="pageStack">
      <section className="pageHero compactHero">
        <div>
          <span className="eyebrowText">Prediction History</span>
          <h1>Saved crop diagnosis reports</h1>
          <p>Search, filter, expand, and download PDF reports from your AI prediction history.</p>
        </div>
      </section>
      <section className="filterBar">
        <input onChange={(event) => setQuery(event.target.value)} placeholder="Search crop, disease, risk" value={query} />
        <select onChange={(event) => setCrop(event.target.value)} value={crop}>
          <option value="">All crops</option>
          <option value="tomato">Tomato</option>
          <option value="mango">Mango</option>
          <option value="coconut">Coconut</option>
        </select>
        <select onChange={(event) => setSeverity(event.target.value)} value={severity}>
          <option value="">All severities</option>
          <option value="Low">Low</option>
          <option value="Medium">Medium</option>
          <option value="High">High</option>
        </select>
        <select onChange={(event) => setView(event.target.value)} value={view}>
          <option value="cards">Card view</option>
          <option value="timeline">Timeline view</option>
          <option value="table">Table view</option>
        </select>
        <button className="secondaryButton" onClick={exportCsv} type="button">Export CSV</button>
      </section>
      <section className={`historyGrid ${view}`}>
        {view !== "table" && filtered.map((item) => (
          <HistoryCard
            item={item}
            key={item.id}
            onDownload={() => downloadPredictionReport({ user, crop: item.crop, prediction: item.prediction, createdAt: item.created_at })}
          />
        ))}
        {view === "table" && filtered.map((item) => (
          <article className="historyTableRow" key={item.id}>
            <strong>{item.crop}</strong>
            <span>{item.prediction?.disease?.replaceAll("_", " ")}</span>
            <span>{item.prediction?.confidence}%</span>
            <button className="textButton" onClick={() => downloadPredictionReport({ user, crop: item.crop, prediction: item.prediction, createdAt: item.created_at })} type="button">Export PDF</button>
          </article>
        ))}
        {filtered.length === 0 && <div className="emptyMarket">No prediction history found.</div>}
      </section>
    </main>
  );
}
