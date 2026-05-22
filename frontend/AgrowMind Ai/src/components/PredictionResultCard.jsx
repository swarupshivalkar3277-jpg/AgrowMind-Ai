import { Link } from "react-router-dom";
import { AlertTriangle, Beaker, Droplets, ShieldCheck, Sprout } from "lucide-react";

import RecommendationCard from "./RecommendationCard";

function fmt(value = "") {
  return value.replaceAll("_", " ");
}

function Badge({ children }) {
  return <span className="softBadge">{children}</span>;
}

export default function PredictionResultCard({ crop, prediction, onDownload }) {
  if (!prediction) {
    return (
      <section className="emptyPrediction">
        <ShieldCheck size={34} />
        <h2>Ready for AI analysis</h2>
        <p>Upload a leaf image to detect disease, severity, treatment, weather impact, and product recommendations.</p>
      </section>
    );
  }

  const confidence = Number(prediction.confidence || 0);

  return (
    <section className="predictionResult">
      <div className="predictionHead">
        <div>
          <span className="eyebrowText">AI Smart Farming Assistant</span>
          <h2>{fmt(prediction.disease)}</h2>
          <p>{crop} analysis completed with actionable farm guidance.</p>
        </div>
        <button className="secondaryButton" onClick={onDownload} type="button">Download PDF</button>
      </div>
      <div className="confidenceBlock">
        <div>
          <span>Confidence</span>
          <strong>{confidence}%</strong>
        </div>
        <div className="confidenceTrack"><span style={{ width: `${Math.min(confidence, 100)}%` }} /></div>
        <Badge>{prediction.severity || "Medium"} severity</Badge>
      </div>
      <div className="aiAdviceGrid">
        <RecommendationCard icon={Beaker} title="Fertilizer" items={prediction.fertilizer} />
        <RecommendationCard icon={Droplets} title="Irrigation" text={prediction.irrigation} />
        <RecommendationCard icon={AlertTriangle} title="Harvest Risk" text={prediction.harvest_risk || "Moderate"} />
        <RecommendationCard icon={Sprout} title="Prevention Tips" items={prediction.prevention} />
      </div>
      <div className="recoveryStrip">
        <strong>Recovery estimate</strong>
        <span>7-14 days with timely treatment and field hygiene.</span>
        <strong>Weather impact</strong>
        <span>High humidity can increase spread. Avoid evening leaf wetness.</span>
      </div>
      <div className="recommendationBand">
        <div>
          <h3>Recommended Products</h3>
          <p>Fertilizers, seeds, pesticides, and saplings matched to this result.</p>
        </div>
        <Link className="primaryButton" to={`/marketplace?crop=${crop}&disease=${prediction.disease}`}>View Marketplace</Link>
      </div>
      <div className="miniProductGrid">
        {(prediction.marketplace_products || []).slice(0, 4).map((product) => (
          <Link className="miniProduct" key={product.id} to={`/marketplace/product/${product.id}`}>
            <img alt={product.name} src={product.image} />
            <span>{product.category}</span>
            <strong>{product.name}</strong>
            <small>Rs. {product.price}</small>
          </Link>
        ))}
      </div>
    </section>
  );
}
