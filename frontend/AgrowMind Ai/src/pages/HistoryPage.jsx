import { useEffect, useMemo, useState } from "react";

import HistoryCard from "../components/HistoryCard";
import { useAuth } from "../context/AuthContext";
import { getHistory } from "../services/authService";
import { downloadPredictionReport } from "../utils/reportPdf";

export default function HistoryPage() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("");

  useEffect(() => {
    getHistory().then(({ data }) => setItems(data.items || [])).catch(() => setItems([]));
  }, []);

  const filtered = useMemo(() => {
    return items.filter((item) => {
      const text = `${item.crop} ${item.prediction?.disease} ${item.prediction?.harvest_risk}`.toLowerCase();
      const matchesQuery = !query || text.includes(query.toLowerCase());
      const matchesSeverity = !severity || item.prediction?.severity === severity;
      return matchesQuery && matchesSeverity;
    });
  }, [items, query, severity]);

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
        <select onChange={(event) => setSeverity(event.target.value)} value={severity}>
          <option value="">All severities</option>
          <option value="Low">Low</option>
          <option value="Medium">Medium</option>
          <option value="High">High</option>
        </select>
      </section>
      <section className="historyGrid">
        {filtered.map((item) => (
          <HistoryCard
            item={item}
            key={item.id}
            onDownload={() => downloadPredictionReport({ user, crop: item.crop, prediction: item.prediction, createdAt: item.created_at })}
          />
        ))}
        {filtered.length === 0 && <div className="emptyMarket">No prediction history found.</div>}
      </section>
    </main>
  );
}
