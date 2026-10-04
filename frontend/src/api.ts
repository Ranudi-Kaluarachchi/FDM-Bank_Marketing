// Typed client for the FastAPI backend. The interfaces mirror the JSON returned by each endpoint.

// One client's input fields, e.g. { age: 35, job: "management", ... }.
export type ClientRecord = Record<string, string | number>;

// Response of POST /api/predict.
export interface Prediction {
  prediction: "yes" | "no";
  probability: number;
  threshold: number;
  likelihood: "low" | "medium" | "high";
}

// Response of GET /api/metadata: model info plus the input schema used to build the form.
export interface Metadata {
  model_name: string;
  threshold: number;
  trained_at: string;
  training_rows: number;
  test_metrics: EvalMetrics;
  features: {
    numeric: Record<string, { min: number; max: number; median: number }>;
    categorical: Record<string, string[]>;
    order: string[];
  };
  defaults: ClientRecord;
  cleaning?: CleaningStep[];
}

// Evaluation metrics of one model on the test set at a given threshold.
export interface EvalMetrics {
  threshold: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  pr_auc: number;
  confusion_matrix: { tn: number; fp: number; fn: number; tp: number };
}

// One trained model's results (tuned parameters, CV score, test metrics, ROC curve points).
export interface ModelResult {
  name: string;
  best_params: Record<string, unknown>;
  cv_roc_auc: number;
  train_seconds: number;
  test: EvalMetrics;
  roc_curve: { fpr: number; tpr: number }[];
}

// Response of GET /api/metrics.
export interface Metrics {
  best_model: string;
  threshold: number;
  test_size: number;
  train_size: number;
  best_model_tuned_test: EvalMetrics;
  feature_importance: { feature: string; importance: number; std: number }[];
  models: ModelResult[];
}

// Subscription rate for one category value (e.g. job = "student").
export interface RateRow {
  category: string;
  count: number;
  rate: number;
}

// One entry of the data-cleaning report.
export interface CleaningStep {
  step: string;
  detail?: string;
  rows_removed?: number;
  unknown_counts?: Record<string, number>;
  nan_counts?: Record<string, number>;
}

// Response of GET /api/insights (EDA aggregates + cleaning report).
export interface InsightsResponse {
  insights: {
    rows: number;
    class_balance: { no: number; yes: number; positive_rate: number };
    rate_by: Record<string, RateRow[]>;
    age_histogram: { bin: string; no: number; yes: number }[];
    campaign_rate: RateRow[];
    numeric_correlation_with_target: Record<string, number>;
  };
  cleaning: { raw_rows: number; clean_rows: number; positive_rate: number; steps: CleaningStep[] };
}

// Response of POST /api/predict/batch.
export interface BatchResponse {
  total: number;
  predicted_yes: number;
  predicted_no: number;
  failed: number;
  results: (ClientRecord & Prediction & { row: number })[];
  errors: { row: number; error: string }[];
}

// Parse a fetch response as JSON, or throw an Error with a readable message.
// FastAPI returns `detail` as a string for HTTP errors, or as a list of field errors for validation (422).
async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail))
        message = body.detail
          .map((d: { loc: string[]; msg: string }) => `${d.loc.slice(1).join(".")}: ${d.msg}`)
          .join("; ");
    } catch {
      /* non-JSON error body */
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

// One function per backend endpoint. URLs are relative; the Vite proxy forwards /api to the backend.
export const api = {
  health: () => fetch("/api/health").then((r) => handle<{ status: string; model_loaded: boolean }>(r)),
  metadata: () => fetch("/api/metadata").then((r) => handle<Metadata>(r)),
  metrics: () => fetch("/api/metrics").then((r) => handle<Metrics>(r)),
  insights: () => fetch("/api/insights").then((r) => handle<InsightsResponse>(r)),
  predict: (record: ClientRecord) =>
    fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(record),
    }).then((r) => handle<Prediction>(r)),
  predictBatch: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return fetch("/api/predict/batch", { method: "POST", body: form }).then((r) => handle<BatchResponse>(r));
  },
};
