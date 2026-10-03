import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, type Metrics } from "../api";
import { pct } from "../fields";

const COLORS = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c", "#0891b2"];
const METRIC_KEYS = ["roc_auc", "pr_auc", "f1", "precision", "recall", "accuracy"] as const;

export default function ModelsPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.metrics().then(setMetrics).catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <div className="alert error">{error}</div>;
  if (!metrics) return <div className="card">Loading…</div>;

  const tuned = metrics.best_model_tuned_test;
  const cm = tuned.confusion_matrix;
  const barData = metrics.models.map((m) => ({
    name: m.name,
    "ROC-AUC": m.test.roc_auc,
    "PR-AUC": m.test.pr_auc,
    F1: m.test.f1,
  }));
  const importance = metrics.feature_importance.filter((f) => f.importance > 0).slice(0, 12);

  return (
    <div className="stack">
      <div className="kpis">
        <div className="kpi"><span>Selected model</span><strong>{metrics.best_model}</strong></div>
        <div className="kpi"><span>Test ROC-AUC</span><strong>{tuned.roc_auc.toFixed(3)}</strong></div>
        <div className="kpi"><span>F1 @ threshold {tuned.threshold.toFixed(2)}</span><strong>{tuned.f1.toFixed(3)}</strong></div>
        <div className="kpi"><span>Recall / Precision</span><strong>{pct(tuned.recall, 0)} / {pct(tuned.precision, 0)}</strong></div>
      </div>

      <div className="card">
        <h2>Model comparison</h2>
        <p className="muted">
          Trained on {metrics.train_size.toLocaleString()} rows, evaluated on a held-out stratified test set of{" "}
          {metrics.test_size.toLocaleString()} rows. Hyper-parameters were tuned with 3-fold cross-validation, and
          the model with the best cross-validated ROC-AUC was selected. The metrics below use a 0.5 threshold.
        </p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Model</th>
                <th>CV ROC-AUC</th>
                {METRIC_KEYS.map((k) => <th key={k}>{k.replace("_", "-").toUpperCase()}</th>)}
                <th>Best params</th>
                <th>Train time</th>
              </tr>
            </thead>
            <tbody>
              {[...metrics.models].sort((a, b) => b.cv_roc_auc - a.cv_roc_auc).map((m) => (
                <tr key={m.name} className={m.name === metrics.best_model ? "highlight" : ""}>
                  <td>{m.name}{m.name === metrics.best_model && " ★"}</td>
                  <td>{m.cv_roc_auc.toFixed(3)}</td>
                  {METRIC_KEYS.map((k) => <td key={k}>{m.test[k].toFixed(3)}</td>)}
                  <td className="mono">
                    {Object.entries(m.best_params).map(([k, v]) => `${k}=${v ?? "None"}`).join(", ") || "default"}
                  </td>
                  <td>{m.train_seconds}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="two-col">
        <div className="card">
          <h3>Test-set scores</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" height={60} />
              <YAxis domain={[0, 1]} />
              <Tooltip formatter={(v: number) => v.toFixed(3)} />
              <Legend />
              <Bar dataKey="ROC-AUC" fill={COLORS[0]} />
              <Bar dataKey="PR-AUC" fill={COLORS[1]} />
              <Bar dataKey="F1" fill={COLORS[4]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h3>ROC curves</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" dataKey="fpr" domain={[0, 1]} label={{ value: "False positive rate", position: "insideBottom", offset: -4 }} />
              <YAxis type="number" dataKey="tpr" domain={[0, 1]} label={{ value: "True positive rate", angle: -90, position: "insideLeft" }} />
              <Tooltip formatter={(v: number) => v.toFixed(3)} />
              <Legend verticalAlign="top" />
              {metrics.models.map((m, i) => (
                <Line key={m.name} data={m.roc_curve} dataKey="tpr" name={m.name} stroke={COLORS[i % COLORS.length]}
                  dot={false} strokeWidth={m.name === metrics.best_model ? 3 : 1.5} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="two-col">
        <div className="card">
          <h3>Confusion matrix: {metrics.best_model} (threshold {tuned.threshold.toFixed(2)})</h3>
          <div className="cm">
            <div />
            <div className="cm-head">Predicted no</div>
            <div className="cm-head">Predicted yes</div>
            <div className="cm-head">Actual no</div>
            <div className="cm-cell good">{cm.tn.toLocaleString()}<small>true negatives</small></div>
            <div className="cm-cell bad">{cm.fp.toLocaleString()}<small>false positives</small></div>
            <div className="cm-head">Actual yes</div>
            <div className="cm-cell bad">{cm.fn.toLocaleString()}<small>false negatives</small></div>
            <div className="cm-cell good">{cm.tp.toLocaleString()}<small>true positives</small></div>
          </div>
          <p className="muted small">
            The threshold was chosen to maximise F1 on out-of-fold training predictions, so the test set was never
            used for tuning.
          </p>
        </div>

        <div className="card">
          <h3>Feature importance (permutation, ROC-AUC drop)</h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={importance} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis type="category" dataKey="feature" width={80} interval={0} />
              <Tooltip formatter={(v: number) => v.toFixed(4)} />
              <Bar dataKey="importance" fill={COLORS[0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
