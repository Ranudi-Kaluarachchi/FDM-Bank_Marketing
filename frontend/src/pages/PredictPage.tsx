// "Predict client" tab: a form for one client's details and the model's prediction.
import { FormEvent, useState } from "react";
import { api, type ClientRecord, type Metadata, type Prediction } from "../api";
import { FIELDS, GROUPS, NUMERIC_LIMITS, pct } from "../fields";

// Example of a high-potential client (previous campaign success, March, cellular) for the preset button.
const PROMISING: ClientRecord = {
  age: 31, job: "student", marital: "single", education: "tertiary", default: "no", balance: 4200,
  housing: "no", loan: "no", contact: "cellular", day: 12, month: "mar", campaign: 1,
  pdays: 95, previous: 2, poutcome: "success",
};

export default function PredictPage({ metadata }: { metadata: Metadata }) {
  // Form starts with the "typical client" defaults supplied by the backend.
  const [form, setForm] = useState<ClientRecord>({ ...metadata.defaults });
  const [result, setResult] = useState<Prediction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Which fields are numbers (number inputs) and which are categories (dropdowns), with allowed values.
  const { numeric, categorical } = metadata.features;

  // Update one field; numeric fields are stored as numbers. Any old result is cleared because it no longer matches.
  const update = (name: string, value: string) => {
    setForm((f) => ({ ...f, [name]: name in numeric ? (value === "" ? "" : Number(value)) : value }));
    setResult(null);
  };

  // Send the form to POST /api/predict and show the result (or the validation error).
  const submit = async (e: FormEvent) => {
    e.preventDefault(); // stop the browser from reloading the page
    setLoading(true);
    setError(null);
    try {
      setResult(await api.predict(form));
    } catch (err) {
      setError((err as Error).message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  // Fill the whole form with a preset example.
  const preset = (values: ClientRecord) => {
    setForm({ ...values });
    setResult(null);
    setError(null);
  };

  return (
    <div className="predict-layout">
      <form className="card" onSubmit={submit}>
        <div className="card-head">
          <h2>Client details</h2>
          <div className="preset-buttons">
            <button type="button" className="ghost" onClick={() => preset(metadata.defaults)}>
              Typical client
            </button>
            <button type="button" className="ghost" onClick={() => preset(PROMISING)}>
              Promising lead
            </button>
          </div>
        </div>

        {/* One fieldset per group (profile, finances, ...); fields are generated from the backend metadata */}
        {GROUPS.map((group) => (
          <fieldset key={group}>
            <legend>{group}</legend>
            <div className="grid">
              {metadata.features.order
                .filter((name) => FIELDS[name]?.group === group)
                .map((name) => (
                  <label key={name} className="field">
                    <span>{FIELDS[name].label}</span>
                    {/* Categorical fields -> dropdown of allowed values; numeric fields -> number input with limits */}
                    {name in categorical ? (
                      <select value={String(form[name])} onChange={(e) => update(name, e.target.value)}>
                        {categorical[name].map((opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="number"
                        required
                        step={1}
                        min={NUMERIC_LIMITS[name]?.min}
                        max={NUMERIC_LIMITS[name]?.max}
                        value={form[name]}
                        onChange={(e) => update(name, e.target.value)}
                      />
                    )}
                    {FIELDS[name].help && <small>{FIELDS[name].help}</small>}
                  </label>
                ))}
            </div>
          </fieldset>
        ))}

        <button type="submit" className="primary" disabled={loading}>
          {loading ? "Predicting…" : "Predict subscription"}
        </button>
        {error && <div className="alert error">{error}</div>}
      </form>

      {/* Result panel: verdict, score, score bar with threshold marker, and lead priority */}
      <aside className="card result-card">
        <h2>Prediction</h2>
        {!result && <p className="muted">Fill in the client details and click “Predict subscription”.</p>}
        {result && (
          <>
            <div className={`verdict ${result.prediction}`}>
              {result.prediction === "yes" ? "Likely to subscribe" : "Unlikely to subscribe"}
            </div>
            <div className="prob-value">{pct(result.probability)}</div>
            <div className="muted">subscription score</div>
            {/* Filled bar = score; orange tick = decision threshold */}
            <div className="prob-bar">
              <div className="prob-fill" style={{ width: pct(result.probability) }} />
              <div className="prob-threshold" style={{ left: pct(result.threshold) }} title="Decision threshold" />
            </div>
            <div className="prob-legend">
              <span>0%</span>
              <span>threshold {pct(result.threshold)}</span>
              <span>100%</span>
            </div>
            <p className={`likelihood ${result.likelihood}`}>
              Lead priority: <strong>{result.likelihood}</strong>
            </p>
            <p className="muted small">
              Few clients subscribe overall, so training up-weights subscribers. The score therefore ranks clients
              rather than giving a calibrated probability, and the threshold was tuned to maximise F1. A “yes” flags
              a client worth calling first.
            </p>
          </>
        )}
      </aside>
    </div>
  );
}
