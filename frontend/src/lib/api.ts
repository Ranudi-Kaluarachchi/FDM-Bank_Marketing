import { toast } from "sonner";

export type Likelihood = "low" | "medium" | "high";
export interface Metrics {
  accuracy: number; precision: number; recall: number; f1: number; roc_auc: number; pr_auc: number;
  threshold?: number;
  confusion_matrix?: { tn: number; fp: number; fn: number; tp: number };
}
export interface Metadata {
  model_name: string; threshold: number; trained_at: string; training_rows: number;
  test_metrics: Metrics;
  features: { numeric: Record<string, { min: number; max: number; median: number }>; categorical: Record<string, string[]>; order: string[] };
  defaults: Record<string, string | number>;
}
export interface Prediction { prediction: "yes" | "no"; probability: number; threshold: number; likelihood: Likelihood }
export interface BatchRow extends Record<string, unknown> { row: number; prediction: "yes" | "no"; probability: number; likelihood: Likelihood }
export interface BatchResult { total: number; predicted_yes: number; predicted_no: number; failed: number; results: BatchRow[]; errors: { row: number; error: string }[] }
export interface ModelInfo { name: string; cv_roc_auc: number; train_seconds: number; test: Metrics; roc_curve: { fpr: number; tpr: number }[] }
export interface MetricsResponse { best_model: string; threshold: number; best_model_tuned_test: Metrics; feature_importance: { feature: string; importance: number; std: number }[]; models: ModelInfo[] }
export interface RateRow { category: string; count: number; rate: number }
export interface InsightsResponse {
  insights: {
    rows: number; class_balance: { no: number; yes: number; positive_rate: number };
    rate_by: Record<string, RateRow[]>; age_histogram: { bin: string; no: number; yes: number }[];
    campaign_rate: RateRow[]; numeric_correlation_with_target: Record<string, number>;
  };
  cleaning: { raw_rows: number; clean_rows: number; positive_rate: number; steps: { step: string; detail?: string; rows_removed?: number }[] };
}

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "";

export class ApiError extends Error {}

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).slice(1).join(".") || "field"}: ${d.msg}`).join("; ");
  return "Request failed";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  const ct = res.headers.get("content-type") ?? "";
  if (!ct.includes("application/json")) throw new Error("Non-JSON response");
  const body = await res.json();
  if (!res.ok) throw new ApiError(formatDetail(body?.detail));
  return body as T;
}

/** Tries the real API; on network/format failure falls back to mock. API validation errors are toasted and re-thrown. */
async function withFallback<T>(fn: () => Promise<T>, mock: () => T | Promise<T>): Promise<{ data: T; demo: boolean }> {
  try {
    return { data: await fn(), demo: false };
  } catch (e) {
    if (e instanceof ApiError) {
      toast.error(e.message);
      throw e;
    }
    return { data: await mock(), demo: true };
  }
}

export const api = {
  metadata: () => withFallback(() => request<Metadata>("/api/metadata"), () => MOCK_METADATA),
  metrics: () => withFallback(() => request<MetricsResponse>("/api/metrics"), () => MOCK_METRICS),
  insights: () => withFallback(() => request<InsightsResponse>("/api/insights"), () => MOCK_INSIGHTS),
  predict: (input: Record<string, unknown>) =>
    withFallback(
      () => request<Prediction>("/api/predict", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) }),
      () => mockPredict(input),
    ),
  predictBatch: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return withFallback(() => request<BatchResult>("/api/predict/batch", { method: "POST", body: fd }), () => mockBatch(file));
  },
};

// ---------------- Mock data ----------------
const CAT = {
  job: ["admin.", "blue-collar", "entrepreneur", "housemaid", "management", "retired", "self-employed", "services", "student", "technician", "unemployed"],
  marital: ["divorced", "married", "single"],
  education: ["primary", "secondary", "tertiary"],
  default: ["no", "yes"], housing: ["no", "yes"], loan: ["no", "yes"],
  contact: ["cellular", "telephone", "unknown"],
  month: ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"],
  poutcome: ["failure", "other", "success", "unknown"],
};

export const MOCK_METADATA: Metadata = {
  model_name: "Gradient Boosting",
  threshold: 0.32,
  trained_at: "2026-09-28T14:12:00Z",
  training_rows: 36168,
  test_metrics: { accuracy: 0.884, precision: 0.512, recall: 0.618, f1: 0.56, roc_auc: 0.927, pr_auc: 0.598, threshold: 0.32, confusion_matrix: { tn: 7311, fp: 674, fn: 404, tp: 653 } },
  features: {
    numeric: {
      age: { min: 18, max: 95, median: 39 }, balance: { min: -8019, max: 102127, median: 448 },
      day: { min: 1, max: 31, median: 16 }, campaign: { min: 1, max: 63, median: 2 },
      pdays: { min: -1, max: 871, median: -1 }, previous: { min: 0, max: 275, median: 0 },
    },
    categorical: CAT,
    order: ["age", "job", "marital", "education", "default", "balance", "housing", "loan", "contact", "day", "month", "campaign", "pdays", "previous", "poutcome"],
  },
  defaults: { age: 39, job: "management", marital: "married", education: "secondary", default: "no", balance: 448, housing: "yes", loan: "no", contact: "cellular", day: 16, month: "may", campaign: 2, pdays: -1, previous: 0, poutcome: "unknown" },
};

function likelihood(p: number): Likelihood { return p >= 0.5 ? "high" : p >= 0.2 ? "medium" : "low"; }

export function mockPredict(i: Record<string, unknown>): Prediction {
  const n = (k: string) => Number(i[k] ?? 0);
  let z = -2.6;
  z += i.poutcome === "success" ? 2.3 : i.poutcome === "failure" ? -0.2 : 0;
  z += ["mar", "sep", "oct", "dec"].includes(String(i.month)) ? 1.4 : i.month === "may" ? -0.5 : 0;
  z += i.contact === "unknown" ? -1 : 0.2;
  z += i.housing === "yes" ? -0.6 : 0.3;
  z += i.loan === "yes" ? -0.4 : 0;
  z += ["student", "retired"].includes(String(i.job)) ? 0.7 : i.job === "blue-collar" ? -0.3 : 0;
  z += i.education === "tertiary" ? 0.25 : 0;
  z += Math.min(n("balance"), 20000) / 20000 * 0.5;
  z -= Math.min(n("campaign") - 1, 10) * 0.12;
  z += n("age") > 60 ? 0.8 : n("age") < 25 ? 0.4 : 0;
  z += Math.min(n("previous"), 5) * 0.1;
  const p = 1 / (1 + Math.exp(-z));
  const t = MOCK_METADATA.threshold;
  return { prediction: p >= t ? "yes" : "no", probability: p, threshold: t, likelihood: likelihood(p) };
}

async function mockBatch(file: File): Promise<BatchResult> {
  const text = await file.text();
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (!lines.length) return { total: 0, predicted_yes: 0, predicted_no: 0, failed: 0, results: [], errors: [] };
  const sep = (lines[0].match(/;/g)?.length ?? 0) > (lines[0].match(/,/g)?.length ?? 0) ? ";" : ",";
  const clean = (s: string) => s.trim().replace(/^"|"$/g, "");
  const header = lines[0].split(sep).map(clean);
  const results: BatchRow[] = [];
  const errors: { row: number; error: string }[] = [];
  const required = MOCK_METADATA.features.order;
  const missing = required.filter((r) => !header.includes(r));
  lines.slice(1).forEach((line, idx) => {
    const row = idx + 1;
    const vals = line.split(sep).map(clean);
    const rec: Record<string, unknown> = {};
    header.forEach((h, j) => { if (required.includes(h)) rec[h] = MOCK_METADATA.features.numeric[h] ? Number(vals[j]) : vals[j]; });
    if (missing.length) return errors.push({ row, error: `Missing columns: ${missing.join(", ")}` });
    const bad = Object.entries(rec).find(([k, v]) => MOCK_METADATA.features.numeric[k] && Number.isNaN(v));
    if (bad) return errors.push({ row, error: `Invalid number for '${bad[0]}'` });
    results.push({ row, ...rec, ...mockPredict(rec) });
  });
  const yes = results.filter((r) => r.prediction === "yes").length;
  return { total: lines.length - 1, predicted_yes: yes, predicted_no: results.length - yes, failed: errors.length, results, errors };
}

function roc(power: number) {
  return Array.from({ length: 21 }, (_, k) => { const fpr = k / 20; return { fpr, tpr: Math.pow(fpr, power) }; });
}

export const MOCK_METRICS: MetricsResponse = {
  best_model: "Gradient Boosting",
  threshold: 0.32,
  best_model_tuned_test: MOCK_METADATA.test_metrics,
  feature_importance: [
    { feature: "poutcome", importance: 0.071, std: 0.006 }, { feature: "month", importance: 0.064, std: 0.005 },
    { feature: "contact", importance: 0.048, std: 0.004 }, { feature: "housing", importance: 0.039, std: 0.004 },
    { feature: "age", importance: 0.027, std: 0.003 }, { feature: "day", importance: 0.022, std: 0.003 },
    { feature: "balance", importance: 0.016, std: 0.002 }, { feature: "campaign", importance: 0.014, std: 0.002 },
    { feature: "pdays", importance: 0.012, std: 0.002 }, { feature: "job", importance: 0.01, std: 0.002 },
    { feature: "loan", importance: 0.008, std: 0.001 }, { feature: "education", importance: 0.005, std: 0.001 },
    { feature: "marital", importance: 0.004, std: 0.001 }, { feature: "previous", importance: 0.003, std: 0.001 },
    { feature: "default", importance: 0.001, std: 0.0005 },
  ],
  models: [
    { name: "Logistic Regression", cv_roc_auc: 0.771, train_seconds: 1.8, test: { accuracy: 0.892, precision: 0.645, recall: 0.214, f1: 0.322, roc_auc: 0.768, pr_auc: 0.402 }, roc_curve: roc(0.38) },
    { name: "Random Forest", cv_roc_auc: 0.789, train_seconds: 14.2, test: { accuracy: 0.894, precision: 0.637, recall: 0.252, f1: 0.361, roc_auc: 0.787, pr_auc: 0.428 }, roc_curve: roc(0.34) },
    { name: "Gradient Boosting", cv_roc_auc: 0.796, train_seconds: 22.6, test: { accuracy: 0.896, precision: 0.664, recall: 0.243, f1: 0.356, roc_auc: 0.797, pr_auc: 0.447 }, roc_curve: roc(0.31) },
    { name: "Decision Tree", cv_roc_auc: 0.712, train_seconds: 0.9, test: { accuracy: 0.871, precision: 0.448, recall: 0.302, f1: 0.361, roc_auc: 0.709, pr_auc: 0.297 }, roc_curve: roc(0.5) },
  ],
};
MOCK_METRICS.best_model_tuned_test = { accuracy: 0.858, precision: 0.398, recall: 0.481, f1: 0.436, roc_auc: 0.797, pr_auc: 0.447, threshold: 0.32, confusion_matrix: { tn: 7215, fp: 770, fn: 549, tp: 508 } };
MOCK_METADATA.test_metrics = MOCK_METRICS.best_model_tuned_test;
MOCK_METADATA.model_name = MOCK_METRICS.best_model;

const r = (category: string, count: number, rate: number): RateRow => ({ category, count, rate });
export const MOCK_INSIGHTS: InsightsResponse = {
  insights: {
    rows: 45211,
    class_balance: { no: 39922, yes: 5289, positive_rate: 0.117 },
    rate_by: {
      job: [r("student", 938, 0.287), r("retired", 2264, 0.228), r("unemployed", 1303, 0.155), r("management", 9458, 0.138), r("admin.", 5171, 0.122), r("self-employed", 1579, 0.118), r("technician", 7597, 0.111), r("services", 4154, 0.089), r("housemaid", 1240, 0.088), r("entrepreneur", 1487, 0.083), r("blue-collar", 9732, 0.073)],
      marital: [r("single", 12790, 0.149), r("divorced", 5207, 0.119), r("married", 27214, 0.101)],
      education: [r("tertiary", 13301, 0.15), r("secondary", 23202, 0.106), r("primary", 6851, 0.086)],
      month: [r("jan", 1403, 0.101), r("feb", 2649, 0.166), r("mar", 477, 0.52), r("apr", 2932, 0.197), r("may", 13766, 0.067), r("jun", 5341, 0.102), r("jul", 6895, 0.091), r("aug", 6247, 0.11), r("sep", 579, 0.465), r("oct", 738, 0.438), r("nov", 3970, 0.101), r("dec", 214, 0.467)],
      poutcome: [r("success", 1511, 0.647), r("other", 1840, 0.167), r("failure", 4901, 0.126), r("unknown", 36959, 0.092)],
      contact: [r("cellular", 29285, 0.149), r("telephone", 2906, 0.134), r("unknown", 13020, 0.041)],
      housing: [r("no", 20081, 0.167), r("yes", 25130, 0.077)],
      loan: [r("no", 37967, 0.127), r("yes", 7244, 0.067)],
    },
    age_histogram: [
      { bin: "18–24", no: 588, yes: 220 }, { bin: "25–29", no: 4316, yes: 734 }, { bin: "30–34", no: 9020, yes: 1040 },
      { bin: "35–39", no: 7650, yes: 760 }, { bin: "40–44", no: 5730, yes: 520 }, { bin: "45–49", no: 4710, yes: 440 },
      { bin: "50–54", no: 3820, yes: 380 }, { bin: "55–59", no: 3220, yes: 420 }, { bin: "60–64", no: 520, yes: 310 }, { bin: "65+", no: 348, yes: 465 },
    ],
    campaign_rate: [r("1", 17544, 0.146), r("2", 12505, 0.112), r("3", 5521, 0.112), r("4", 3522, 0.09), r("5", 1764, 0.079), r("6", 1291, 0.071), r("7–10", 2009, 0.06), r("11+", 1055, 0.035)],
    numeric_correlation_with_target: { pdays: 0.104, previous: 0.093, balance: 0.053, age: 0.025, day: -0.028, campaign: -0.073 },
  },
  cleaning: {
    raw_rows: 45211, clean_rows: 45211, positive_rate: 0.117,
    steps: [
      { step: "Loaded raw CSV", detail: "bank-full.csv, ';' separated, 17 columns" },
      { step: "Dropped 'duration'", detail: "Only known after the call ends — would leak the target" },
      { step: "Removed duplicate rows", rows_removed: 0 },
      { step: "Merged 'widowed' into 'divorced'", detail: "Matches UCI documentation" },
      { step: "Encoded target", detail: "y: yes → 1, no → 0" },
      { step: "Stratified 80/20 train/test split", detail: "36,168 train · 9,043 test" },
    ],
  },
};
