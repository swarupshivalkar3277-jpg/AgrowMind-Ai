import { CloudSun } from "lucide-react";

export default function WeatherCard() {
  return (
    <article className="insightCard weatherCard">
      <CloudSun size={28} />
      <span>Weather Impact</span>
      <strong>28°C, light wind</strong>
      <p>Humidity may increase fungal pressure. Schedule leaf inspection after irrigation.</p>
    </article>
  );
}
