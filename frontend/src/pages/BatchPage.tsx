// "Batch scoring" tab: upload a CSV of clients, view ranked predictions and export them.
import { ChangeEvent, useMemo, useState } from "react";
import { api, type BatchResponse, type Metadata } from "../api";
import { pct } from "../fields";

// Rows shown per page in the results table (large files can have tens of thousands of rows).
const PAGE_SIZE = 50;

// Convert result rows back into CSV text for the "Export CSV" button.
function toCsv(rows: Record<string, unknown>[]): string {
  if (!rows.length) return "";
  const cols = Object.keys(rows[0]);
  // Quote values containing commas, quotes or newlines (standard CSV escaping).
  const esc = (v: unknown) => {
    const s = String(v ?? "");
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
}

// Trigger a browser download of `content` as a file called `name`.
function download(name: string, content: string) {
  const url = URL.createObjectURL(new Blob([content], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export default function BatchPage({ metadata }: { metadata: Metadata }) {
  const [file, setFile] = useState<File | null>(null);
  const [data, setData] = useState<BatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(0);               // current results page (0-based)
  const [sortByProb, setSortByProb] = useState(true); // show highest-scoring clients first

  // The 15 input columns, in the order the model expects.
  const columns = metadata.features.order;

  // A new file was chosen: forget any previous results.
  const onFile = (e: ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] ?? null);
    setData(null);
    setError(null);
  };

  // Upload the file to POST /api/predict/batch.
  const run = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      setData(await api.predictBatch(file));
      setPage(0);
    } catch (err) {
      setError((err as Error).message);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  // Results in display order; useMemo avoids re-sorting on every render.
  const rows = useMemo(() => {
    if (!data) return [];
    return sortByProb ? [...data.results].sort((a, b) => b.probability - a.probability) : data.results;
  }, [data, sortByProb]);
  const pageRows = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const pages = Math.ceil(rows.length / PAGE_SIZE);

  // Download a CSV template: header row plus one example row of default values.
  const template = () => {
    const header = columns.join(",");
    const example = columns.map((c) => metadata.defaults[c]).join(",");
    download("client_template.csv", `${header}\n${example}\n`);
  };

  return (
    <div className="stack">
      <div className="card">
        <h2>Score a list of clients</h2>
        <p className="muted">
          Upload a CSV (comma or semicolon separated) with the columns <code>{columns.join(", ")}</code>. Extra
          columns such as <code>y</code> or <code>duration</code> are ignored, so the original UCI{" "}
          <code>bank-full.csv</code> works as-is.
        </p>
        <div className="row">
          <input type="file" accept=".csv,text/csv" onChange={onFile} />
          <button className="primary" disabled={!file || loading} onClick={run}>
            {loading ? "Scoring…" : "Run predictions"}
          </button>
          <button className="ghost" onClick={template}>
            Download template
          </button>
        </div>
        {error && <div className="alert error">{error}</div>}
      </div>

      {data && (
        <>
          {/* Summary counts */}
          <div className="kpis">
            <div className="kpi"><span>Rows</span><strong>{data.total.toLocaleString()}</strong></div>
            <div className="kpi good"><span>Predicted yes</span><strong>{data.predicted_yes.toLocaleString()}</strong></div>
            <div className="kpi"><span>Predicted no</span><strong>{data.predicted_no.toLocaleString()}</strong></div>
            <div className={data.failed ? "kpi bad" : "kpi"}><span>Invalid rows</span><strong>{data.failed}</strong></div>
          </div>

          {/* Validation errors (first 20 shown) */}
          {data.errors.length > 0 && (
            <div className="card">
              <h3>Rows that could not be scored</h3>
              <ul className="errors">
                {data.errors.slice(0, 20).map((e) => (
                  <li key={e.row}>Row {e.row}: {e.error}</li>
                ))}
                {data.errors.length > 20 && <li>…and {data.errors.length - 20} more</li>}
              </ul>
            </div>
          )}

          {/* Paginated results table with sort and export controls */}
          <div className="card">
            <div className="card-head">
              <h3>Results</h3>
              <div className="row">
                <label className="checkbox">
                  <input type="checkbox" checked={sortByProb} onChange={(e) => setSortByProb(e.target.checked)} />
                  Sort by probability
                </label>
                <button className="ghost" onClick={() => download("predictions.csv", toCsv(rows))}>
                  Export CSV
                </button>
              </div>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Row</th>
                    <th>Prediction</th>
                    <th>Probability</th>
                    {columns.map((c) => <th key={c}>{c}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {pageRows.map((r) => (
                    <tr key={r.row}>
                      <td>{r.row}</td>
                      <td><span className={`pill ${r.prediction}`}>{r.prediction}</span></td>
                      <td>{pct(r.probability)}</td>
                      {columns.map((c) => <td key={c}>{String(r[c])}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {pages > 1 && (
              <div className="pager">
                <button className="ghost" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
                <span>Page {page + 1} of {pages}</span>
                <button className="ghost" disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>Next</button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
