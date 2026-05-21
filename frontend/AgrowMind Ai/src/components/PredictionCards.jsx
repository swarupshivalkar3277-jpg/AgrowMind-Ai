function Icon({ name }) {
  const icons = {
    leaf: "M5 19c8 0 14-6 14-14C11 5 5 11 5 19Zm0 0c0-5 4-9 9-9",
    gauge: "M4 14a8 8 0 1 1 16 0M12 14l4-4M8 18h8",
    shield: "M12 3l7 3v5c0 5-3 9-7 10-4-1-7-5-7-10V6l7-3Z",
    flask: "M9 3h6M10 3v6l-4 8a3 3 0 0 0 3 4h6a3 3 0 0 0 3-4l-4-8V3",
    spray: "M8 4h7l1 4H7l1-4ZM9 8v3l-4 4v5h10v-5l-4-4V8M16 6h4M18 4v4",
    drop: "M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11Z",
    sprout: "M12 20V10M12 10C9 6 5 6 4 10c4 1 6 1 8 0ZM12 13c3-4 7-4 8 0-4 1-6 1-8 0Z",
    check: "M5 12l4 4L19 6",
    harvest: "M6 20h12M8 20V9a4 4 0 0 1 8 0v11M6 12h12",
    download: "M12 3v12M7 10l5 5 5-5M5 21h14",
  };

  return (
    <svg aria-hidden="true" className="cardIcon" fill="none" viewBox="0 0 24 24">
      <path d={icons[name]} stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
    </svg>
  );
}

function formatDiseaseName(value = "") {
  return value.replaceAll("_", " ");
}

function InfoCard({ icon, title, children, className = "" }) {
  return (
    <article className={`smartCard ${className}`}>
      <div className="smartCardTitle">
        <Icon name={icon} />
        <span>{title}</span>
      </div>
      {children}
    </article>
  );
}

function TagList({ items = [] }) {
  return (
    <div className="tagList">
      {items.map((item) => (
        <span key={item}>{item}</span>
      ))}
    </div>
  );
}

export function SeverityBadge({ value = "Medium" }) {
  return <span className={`severityBadge severity${value}`}>{value}</span>;
}

export default function PredictionCards({ crop, prediction, onDownload }) {
  if (!prediction) {
    return null;
  }

  return (
    <div className="predictionStack">
      <div className="predictionHero">
        <div>
          <p className="eyebrow">AI Smart Farming Assistant</p>
          <h2>{formatDiseaseName(prediction.disease)}</h2>
          <span className="cropPill">{crop}</span>
        </div>
        <button className="reportButton" onClick={onDownload} type="button">
          <Icon name="download" />
          Report
        </button>
      </div>

      <div className="smartGrid">
        <InfoCard icon="gauge" title="Confidence">
          <strong className="bigMetric">{prediction.confidence}%</strong>
        </InfoCard>
        <InfoCard icon="shield" title="Severity">
          <SeverityBadge value={prediction.severity} />
        </InfoCard>
        <InfoCard icon="harvest" title="Harvest Risk">
          <strong className="riskText">{prediction.harvest_risk}</strong>
        </InfoCard>
        <InfoCard icon="flask" title="Fertilizer">
          <TagList items={prediction.fertilizer} />
        </InfoCard>
        <InfoCard icon="spray" title="Treatment">
          <TagList items={prediction.treatment} />
        </InfoCard>
        <InfoCard icon="drop" title="Irrigation" className="wideCard">
          <p>{prediction.irrigation}</p>
        </InfoCard>
        <InfoCard icon="sprout" title="Organic Solutions">
          <TagList items={prediction.organic_solution} />
        </InfoCard>
        <InfoCard icon="check" title="Prevention">
          <TagList items={prediction.prevention} />
        </InfoCard>
      </div>

      <section className="recommendedProducts">
        <div className="sectionHeader">
          <div>
            <h3>Buy Recommended Products</h3>
            <span>Matched to {crop} and {formatDiseaseName(prediction.disease)}</span>
          </div>
          <Link
            className="secondaryButton"
            to={`/marketplace?crop=${crop}&disease=${prediction.disease}`}
          >
            View Marketplace
          </Link>
        </div>
        <div className="quickBuyLinks">
          <Link to={`/marketplace?crop=${crop}&disease=${prediction.disease}&category=fertilizers`}>
            Buy Fertilizer
          </Link>
          <Link to={`/marketplace?crop=${crop}&disease=${prediction.disease}&category=pesticides`}>
            Buy Treatment
          </Link>
          <Link to={`/marketplace?crop=${crop}&category=trees`}>
            View Tree Marketplace
          </Link>
        </div>
        <div className="miniProductGrid">
          {(prediction.marketplace_products || []).slice(0, 3).map((product) => (
            <Link className="miniProduct" key={product.id} to={`/marketplace/product/${product.id}`}>
              <img alt={product.name} src={product.image} />
              <span>{product.category}</span>
              <strong>{product.name}</strong>
              <small>₹{product.price} - ★ {product.rating}</small>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
import { Link } from "react-router-dom";
