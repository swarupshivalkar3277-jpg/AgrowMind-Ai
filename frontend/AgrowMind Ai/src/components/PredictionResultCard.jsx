import { Link } from "react-router-dom";
import { AlertTriangle, Beaker, Bug, CheckCircle2, ClipboardList, Droplets, ShieldCheck, Sprout, Stethoscope } from "lucide-react";

import EmptyState from "./EmptyState";
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
      <EmptyState
        icon={ShieldCheck}
        title="Ready for AI analysis"
        text="Upload a leaf image to detect disease, severity, treatment, prevention steps, and matched marketplace inputs."
      />
    );
  }

  const confidence = Number(prediction.confidence || 0);
  const recommendation = prediction.recommendation || {};
  const symptoms = recommendation.symptoms || prediction.symptoms || [];
  const causes = recommendation.causes || prediction.causes || [];
  const treatment = recommendation.treatment || prediction.treatment || [];
  const organic = recommendation.organic_solutions || prediction.organic_solutions || prediction.organic_solution || [];
  const chemical = recommendation.chemical_solutions || prediction.chemical_solutions || [];
  const prevention = recommendation.prevention || prediction.prevention || [];
  const staticProducts = recommendation.recommended_products || prediction.recommended_products || [];
  const marketplaceProducts = prediction.marketplace_products || recommendation.marketplace_products || [];
  const severity = prediction.severity || "Medium";
  const timeline = recommendation.spraying_schedule || prediction.spraying_schedule || [
    "Day 1: Remove infected leaves and isolate affected plants.",
    "Day 2-3: Apply recommended treatment in early morning.",
    "Day 7: Recheck spread, repeat spray only if symptoms remain.",
    "Day 14: Review recovery and update prevention routine.",
  ];

  return (
    <section className="predictionResult">
      <div className="diseaseHeroCard">
        <div className="predictionHead">
          <div>
            <span className="eyebrowText">AI Smart Farming Assistant</span>
            <h2>{fmt(prediction.disease)}</h2>
            <p>{crop} analysis completed with actionable farm guidance.</p>
          </div>
          <button className="secondaryButton" onClick={onDownload} type="button">Download PDF</button>
        </div>
        <div className="diagnosisVitals">
          <div className="confidenceGauge" style={{ "--score": `${Math.min(confidence, 100) * 3.6}deg` }}>
            <div>
              <strong>{confidence}%</strong>
              <span>Confidence</span>
            </div>
          </div>
          <div className="vitalsGrid">
            <article><span>Crop</span><strong>{crop}</strong></article>
            <article><span>Severity</span><strong className={`severityPill ${severity.toLowerCase()}`}>{severity}</strong></article>
            <article><span>Status</span><strong>Action needed</strong></article>
          </div>
        </div>
      </div>
      <div className="resultTabs" role="list" aria-label="Prediction sections">
        {["Symptoms", "Causes", "Treatment", "Prevention", "Products"].map((item) => <span key={item} role="listitem">{item}</span>)}
      </div>
      <div className="confidenceBlock">
        <div>
          <span>Confidence score</span>
          <strong>{confidence}%</strong>
        </div>
        <div className="confidenceTrack"><span style={{ width: `${Math.min(confidence, 100)}%` }} /></div>
        <Badge>{severity} severity</Badge>
      </div>
      <div className="aiAdviceGrid">
        <RecommendationCard icon={Stethoscope} title="Symptoms" items={symptoms} />
        <RecommendationCard icon={Bug} title="Causes" items={causes} />
        <RecommendationCard icon={ClipboardList} title="Treatment" items={treatment} />
        <RecommendationCard icon={Sprout} title="Organic Solutions" items={organic} />
        <RecommendationCard icon={Beaker} title="Chemical Solutions" items={chemical} />
        <RecommendationCard icon={Beaker} title="Fertilizer" items={prediction.fertilizer} />
        <RecommendationCard icon={Droplets} title="Irrigation" text={prediction.irrigation} />
        <RecommendationCard icon={AlertTriangle} title="Harvest Risk" text={prediction.harvest_risk || "Moderate"} />
        <RecommendationCard icon={ShieldCheck} title="Prevention Tips" items={prevention} />
        <RecommendationCard icon={ClipboardList} title="Recommended Inputs" items={staticProducts} />
      </div>
      <section className="treatmentTimeline">
        <div className="sectionHeader">
          <div><span className="eyebrowText">Treatment Timeline</span><h3>Next best actions</h3></div>
        </div>
        {timeline.slice(0, 4).map((item, index) => (
          <article key={`${item}-${index}`}>
            <span>{index + 1}</span>
            <p>{item}</p>
          </article>
        ))}
      </section>
      <section className="preventionChecklist">
        <div><span className="eyebrowText">Prevention Checklist</span><h3>Keep this from returning</h3></div>
        {(prevention.length ? prevention : ["Improve airflow", "Avoid overhead watering", "Remove infected leaves"]).slice(0, 5).map((item) => (
          <span key={item}><CheckCircle2 size={17} /> {item}</span>
        ))}
      </section>
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
        {marketplaceProducts.slice(0, 4).map((product) => (
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
