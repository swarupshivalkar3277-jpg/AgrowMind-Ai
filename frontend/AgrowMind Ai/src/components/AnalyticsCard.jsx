import { ResponsiveContainer, Area, AreaChart, CartesianGrid, Tooltip, XAxis } from "recharts";

const data = [
  { day: "Mon", risk: 28 },
  { day: "Tue", risk: 42 },
  { day: "Wed", risk: 36 },
  { day: "Thu", risk: 58 },
  { day: "Fri", risk: 44 },
  { day: "Sat", risk: 33 },
];

export default function AnalyticsCard() {
  return (
    <article className="insightCard chartCard">
      <span>Disease Analytics</span>
      <strong>Risk trend</strong>
      <ResponsiveContainer height={170} width="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="riskFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.45} />
              <stop offset="95%" stopColor="#2563eb" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="day" />
          <Tooltip />
          <Area dataKey="risk" fill="url(#riskFill)" stroke="#10b981" strokeWidth={3} type="monotone" />
        </AreaChart>
      </ResponsiveContainer>
    </article>
  );
}
