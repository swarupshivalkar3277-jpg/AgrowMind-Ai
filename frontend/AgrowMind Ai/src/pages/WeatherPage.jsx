import { CloudRain, CloudSun, Droplets, ThermometerSun, Wind } from "lucide-react";

const forecast = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day, index) => ({
  day,
  temp: 28 + (index % 4),
  rain: 20 + index * 7,
}));

export default function WeatherPage() {
  return (
    <main className="pageStack">
      <section className="pageHero compactHero weatherHero"><div><span className="eyebrowText">Weather Intelligence</span><h1>Crop-aware weather planning</h1><p>Current conditions, 7-day outlook, rainfall risk, wind, humidity, and field advisory in one dedicated page.</p></div></section>
      <section className="statsGrid">
        <article className="statsCard"><ThermometerSun /><span>Temperature</span><strong>29°C</strong></article>
        <article className="statsCard"><Droplets /><span>Humidity</span><strong>74%</strong></article>
        <article className="statsCard"><CloudRain /><span>Rain probability</span><strong>42%</strong></article>
        <article className="statsCard"><Wind /><span>Wind speed</span><strong>11 km/h</strong></article>
      </section>
      <section className="forecastGrid">{forecast.map((item) => <article className="panel forecastCard" key={item.day}><CloudSun /><strong>{item.day}</strong><span>{item.temp}°C</span><small>{item.rain}% rain</small></article>)}</section>
      <section className="panel advisoryPanel"><h2>Crop Advisory</h2><p>High humidity can increase fungal spread. Inspect leaves early morning, avoid evening overhead irrigation, and plan preventive sprays before sustained rainfall.</p><span className="softBadge">Weather warning: moderate disease pressure</span></section>
    </main>
  );
}
