import { useEffect, useState } from "react";
import { api, type Metadata } from "./api";
import PredictPage from "./pages/PredictPage";
import BatchPage from "./pages/BatchPage";
import ModelsPage from "./pages/ModelsPage";
import InsightsPage from "./pages/InsightsPage";

const TABS = [
  { id: "predict", label: "Predict client" },
  { id: "batch", label: "Batch scoring" },
  { id: "models", label: "Model performance" },
  { id: "insights", label: "Data insights" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<TabId>("predict");
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.metadata().then(setMetadata).catch((e: Error) => setError(e.message));
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Term Deposit Subscription Predictor</h1>
          <p className="subtitle">UCI Bank Marketing dataset · Portuguese bank telemarketing campaigns</p>
        </div>
        {metadata && (
          <div className="model-badge">
            <span>Active model</span>
            <strong>{metadata.model_name}</strong>
            <small>ROC-AUC {metadata.test_metrics.roc_auc.toFixed(3)}</small>
          </div>
        )}
      </header>

      <nav className="tabs">
        {TABS.map((t) => (
          <button key={t.id} className={tab === t.id ? "tab active" : "tab"} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>

      <main>
        {error && (
          <div className="alert error">
            Cannot reach the backend: {error}. Start it with <code>uvicorn app.main:app --port 8000</code> from{" "}
            <code>backend/</code>.
          </div>
        )}
        {!error && !metadata && <div className="card">Loading…</div>}
        {metadata && tab === "predict" && <PredictPage metadata={metadata} />}
        {metadata && tab === "batch" && <BatchPage metadata={metadata} />}
        {metadata && tab === "models" && <ModelsPage />}
        {metadata && tab === "insights" && <InsightsPage />}
      </main>
    </div>
  );
}
