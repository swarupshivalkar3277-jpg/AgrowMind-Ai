import { Download, Maximize2 } from "lucide-react";

function fmt(value = "") {
  return value.replaceAll("_", " ");
}

export default function HistoryCard({ item, onDownload }) {
  return (
    <article className="historyCard">
      <div>
        <span>{item.crop}</span>
        <h3>{fmt(item.prediction?.disease)}</h3>
        <p>{new Date(item.created_at).toLocaleString()}</p>
      </div>
      <div className="historyMetrics">
        <strong>{item.prediction?.confidence}%</strong>
        <span>{item.prediction?.severity}</span>
      </div>
      <div className="historyActions">
        <button className="iconTextButton" onClick={onDownload} type="button"><Download size={16} /> PDF</button>
        <button className="iconTextButton" type="button"><Maximize2 size={16} /> Details</button>
      </div>
    </article>
  );
}
