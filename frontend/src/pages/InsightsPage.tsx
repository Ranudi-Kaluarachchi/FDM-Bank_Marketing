// "Data insights" tab: EDA charts and the data-cleaning summary.
import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, type InsightsResponse, type RateRow } from "../api";
import { pct } from "../fields";

// Attributes the user can pick in the "subscription rate by ..." dropdown (keys match insights.rate_by).
const BREAKDOWNS: { key: string; label: string }[] = [
  { key: "month", label: "Month of last contact" },
  { key: "job", label: "Job" },
  { key: "age_group", label: "Age group" },
  { key: "poutcome", label: "Previous campaign outcome" },
  { key: "contact", label: "Contact type" },
  { key: "education", label: "Education" },
  { key: "marital", label: "Marital status" },
  { key: "housing", label: "Housing loan" },
  { key: "loan", label: "Personal loan" },
  { key: "previously_contacted", label: "Previously contacted" },
];

// Reusable bar chart of subscription rate per category; the tooltip also shows the row count (n).
function RateChart({ data, height = 280 }: { data: RateRow[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="category" tick={{ fontSize: 11 }} interval={0} angle={-20} textAnchor="end" height={55} />
        <YAxis tickFormatter={(v: number) => pct(v, 0)} />
        <Tooltip
          formatter={(v: number) => pct(v)}
          labelFormatter={(l, p) => `${l} (n=${p?.[0]?.payload?.count?.toLocaleString() ?? "?"})`}
        />
        <Bar dataKey="rate" name="Subscription rate" fill="#2563eb" />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function InsightsPage() {
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [breakdown, setBreakdown] = useState("month"); // attribute selected in the dropdown

  // Load GET /api/insights once when the tab opens.
  useEffect(() => {
    api.insights().then(setData).catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <div className="alert error">{error}</div>;
  if (!data) return <div className="card">Loading…</div>;

  const { insights, cleaning } = data;
  // Pie chart data: subscribers vs non-subscribers.
  const balance = [
    { name: "No", value: insights.class_balance.no },
    { name: "Yes", value: insights.class_balance.yes },
  ];
  // Convert { age: 0.02, ... } into [{ feature: "age", value: 0.02 }, ...] for the bar chart.
  const corr = Object.entries(insights.numeric_correlation_with_target).map(([feature, value]) => ({ feature, value }));

  return (
    <div className="stack">
      {/* Dataset headline numbers */}
      <div className="kpis">
        <div className="kpi"><span>Raw rows</span><strong>{cleaning.raw_rows.toLocaleString()}</strong></div>
        <div className="kpi"><span>Rows after cleaning</span><strong>{cleaning.clean_rows.toLocaleString()}</strong></div>
        <div className="kpi"><span>Subscription rate</span><strong>{pct(insights.class_balance.positive_rate)}</strong></div>
        <div className="kpi"><span>Input features</span><strong>15</strong></div>
      </div>

      <div className="two-col">
        {/* Pie chart of yes vs no (grey = no, green = yes) */}
        <div className="card">
          <h3>Class balance</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={balance} dataKey="value" nameKey="name" outerRadius={95} label={(e) => `${e.name}: ${e.value.toLocaleString()}`}>
                <Cell fill="#94a3b8" />
                <Cell fill="#16a34a" />
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <p className="muted small">
            The classes are heavily imbalanced, which is why the models use class weighting and are judged on ROC-AUC,
            PR-AUC and F1 rather than accuracy.
          </p>
        </div>

        {/* Cleaning steps read from artifacts/cleaning_report.json, plus the in-pipeline steps */}
        <div className="card">
          <h3>Data cleaning steps</h3>
          <ol className="steps">
            {cleaning.steps.map((s) => (
              <li key={s.step}>
                <strong>{s.step.replace(/_/g, " ")}</strong>
                {s.detail && <> — {s.detail}</>}
                {s.rows_removed !== undefined && <> — {s.rows_removed} rows removed</>}
                {s.unknown_counts && Object.keys(s.unknown_counts).length > 0 && (
                  <div className="muted small">
                    'unknown' values:{" "}
                    {Object.entries(s.unknown_counts).map(([k, v]) => `${k} ${v.toLocaleString()}`).join(", ")}
                  </div>
                )}
              </li>
            ))}
            <li>
              <strong>inside model pipeline</strong> — derive features (previously contacted flag, days since previous
              contact, signed log balance, total contacts, age group), cap outliers at the 1st/99th percentile, scale
              numeric features and one-hot encode categorical ones
            </li>
          </ol>
        </div>
      </div>

      {/* Subscription rate by the attribute chosen in the dropdown */}
      <div className="card">
        <div className="card-head">
          <h3>Subscription rate by {BREAKDOWNS.find((b) => b.key === breakdown)?.label.toLowerCase()}</h3>
          <select value={breakdown} onChange={(e) => setBreakdown(e.target.value)}>
            {BREAKDOWNS.map((b) => <option key={b.key} value={b.key}>{b.label}</option>)}
          </select>
        </div>
        <RateChart data={insights.rate_by[breakdown]} height={320} />
      </div>

      <div className="two-col">
        {/* Stacked histogram: clients per 5-year age bin, split by outcome */}
        <div className="card">
          <h3>Age distribution by outcome</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={insights.age_histogram}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="bin" tick={{ fontSize: 11 }} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="no" stackId="a" fill="#94a3b8" name="Did not subscribe" />
              <Bar dataKey="yes" stackId="a" fill="#16a34a" name="Subscribed" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        {/* More calls in a campaign -> lower subscription rate */}
        <div className="card">
          <h3>Subscription rate by number of calls this campaign</h3>
          <RateChart data={insights.campaign_rate} />
        </div>
      </div>

      {/* Pearson correlation of each numeric feature with the target (green = positive, red = negative) */}
      <div className="card">
        <h3>Correlation of numeric features with subscription</h3>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={corr}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="feature" />
            <YAxis />
            <Tooltip formatter={(v: number) => v.toFixed(3)} />
            <Bar dataKey="value" name="Pearson r">
              {corr.map((c) => <Cell key={c.feature} fill={c.value >= 0 ? "#16a34a" : "#dc2626"} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
