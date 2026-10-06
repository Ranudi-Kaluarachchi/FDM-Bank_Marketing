import { useMemo, useRef, useState } from "react";
import { ArrowUpDown, Download, FileUp, UploadCloud } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type BatchResult, type BatchRow } from "@/lib/api";
import { pct } from "@/lib/fields";
import { cn } from "@/lib/utils";
import { Empty, Kpi, LikelihoodBadge, Panel, PredictionBadge } from "./shared";

const PAGE = 15;
type SortKey = "row" | "probability" | "age" | "balance";

export function BatchPage({ onDemo }: { onDemo: (d: boolean) => void }) {
  const [data, setData] = useState<BatchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [drag, setDrag] = useState(false);
  const [fileName, setFileName] = useState("");
  const [filter, setFilter] = useState<"all" | "yes" | "no">("all");
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "probability", dir: -1 });
  const [page, setPage] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const handle = async (file?: File) => {
    if (!file) return;
    if (!/\.csv$/i.test(file.name)) return toast.error("Please upload a .csv file");
    if (file.size > 10 * 1024 * 1024) return toast.error("File is larger than 10 MB");
    setFileName(file.name); setLoading(true); setPage(0);
    try { const r = await api.predictBatch(file); setData(r.data); onDemo(r.demo); } catch { /* toasted */ } finally { setLoading(false); }
  };

  const rows = useMemo(() => {
    if (!data) return [];
    const f = data.results.filter((r) => filter === "all" || r.prediction === filter);
    return [...f].sort((a, b) => (Number(a[sort.key]) - Number(b[sort.key])) * sort.dir);
  }, [data, filter, sort]);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  const shown = rows.slice(page * PAGE, page * PAGE + PAGE);

  const toggleSort = (key: SortKey) => setSort((s) => ({ key, dir: s.key === key ? (s.dir === 1 ? -1 : 1) : -1 }));

  const download = () => {
    if (!data?.results.length) return;
    const cols = Object.keys(data.results[0]);
    const esc = (v: unknown) => { const s = String(v ?? ""); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
    const csv = [cols.join(","), ...data.results.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = fileName.replace(/\.csv$/i, "") + "_predictions.csv";
    a.click();
  };

  const SortHead = ({ k, children }: { k: SortKey; children: string }) => (
    <TableHead><button type="button" onClick={() => toggleSort(k)} className="inline-flex items-center gap-1 hover:text-foreground">{children}<ArrowUpDown className={cn("h-3 w-3", sort.key === k ? "text-primary" : "opacity-40")} /></button></TableHead>
  );

  return (
    <div className="space-y-6">
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); handle(e.dataTransfer.files[0]); }}
        onClick={() => inputRef.current?.click()}
        className={cn("card-soft flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed bg-card px-6 py-12 text-center transition-colors", drag ? "border-primary bg-accent" : "border-border hover:border-primary/50")}
      >
        <input ref={inputRef} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => { handle(e.target.files?.[0]); e.target.value = ""; }} />
        <div className="mb-3 rounded-full bg-accent p-3 text-primary"><UploadCloud className="h-6 w-6" /></div>
        <p className="font-semibold">{loading ? "Scoring clients…" : "Drop a CSV here or click to browse"}</p>
        <p className="mt-1 text-sm text-muted-foreground">Max 10 MB · comma or semicolon separated · same 15 columns as the form</p>
        {fileName && <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-primary"><FileUp className="h-3.5 w-3.5" />{fileName}</p>}
      </div>

      {loading && <div className="grid gap-4 md:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-2xl" />)}</div>}

      {data && !loading && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Kpi label="Total rows" value={data.total.toLocaleString()} />
            <Kpi label="Predicted yes" value={data.predicted_yes.toLocaleString()} tone="yes" sub={pct(data.total ? data.predicted_yes / data.total : 0)} />
            <Kpi label="Predicted no" value={data.predicted_no.toLocaleString()} tone="no" sub={pct(data.total ? data.predicted_no / data.total : 0)} />
            <Kpi label="Failed" value={data.failed.toLocaleString()} tone={data.failed ? "destructive" : "default"} />
          </div>

          <Panel
            title="Results"
            description={`${rows.length.toLocaleString()} rows`}
            action={
              <div className="flex flex-wrap items-center gap-2">
                <ToggleGroup type="single" size="sm" variant="outline" value={filter} onValueChange={(v) => { if (v) { setFilter(v as typeof filter); setPage(0); } }}>
                  <ToggleGroupItem value="all">All</ToggleGroupItem><ToggleGroupItem value="yes">Yes</ToggleGroupItem><ToggleGroupItem value="no">No</ToggleGroupItem>
                </ToggleGroup>
                <Button size="sm" variant="outline" onClick={download} disabled={!data.results.length}><Download className="mr-1.5 h-4 w-4" />Download CSV</Button>
              </div>
            }
          >
            {shown.length === 0 ? <Empty title="No rows to show" hint="Try another filter or upload a different file" /> : (
              <>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader><TableRow>
                      <SortHead k="row">Row</SortHead><SortHead k="age">Age</SortHead><TableHead>Job</TableHead><SortHead k="balance">Balance</SortHead><TableHead>Month</TableHead>
                      <TableHead>Prediction</TableHead><SortHead k="probability">Probability</SortHead><TableHead>Likelihood</TableHead>
                    </TableRow></TableHeader>
                    <TableBody>{shown.map((r: BatchRow) => (
                      <TableRow key={r.row}>
                        <TableCell className="text-muted-foreground tabular-nums">{r.row}</TableCell>
                        <TableCell className="tabular-nums">{String(r.age ?? "—")}</TableCell>
                        <TableCell className="capitalize">{String(r.job ?? "—")}</TableCell>
                        <TableCell className="tabular-nums">€{Number(r.balance ?? 0).toLocaleString()}</TableCell>
                        <TableCell className="capitalize">{String(r.month ?? "—")}</TableCell>
                        <TableCell><PredictionBadge value={r.prediction} /></TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className="h-2 w-24 rounded-full bg-muted"><div className={cn("h-full rounded-full", r.prediction === "yes" ? "bg-yes" : "bg-no")} style={{ width: `${r.probability * 100}%` }} /></div>
                            <span className="w-12 text-right text-xs tabular-nums">{pct(r.probability)}</span>
                          </div>
                        </TableCell>
                        <TableCell><LikelihoodBadge value={r.likelihood} /></TableCell>
                      </TableRow>
                    ))}</TableBody>
                  </Table>
                </div>
                <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
                  <span>Page {page + 1} of {pages}</span>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>Previous</Button>
                    <Button size="sm" variant="outline" disabled={page >= pages - 1} onClick={() => setPage((p) => p + 1)}>Next</Button>
                  </div>
                </div>
              </>
            )}
          </Panel>

          {data.errors.length > 0 && (
            <Panel title="Row errors" description={`${data.errors.length} rows could not be scored`}>
              <ul className="max-h-64 space-y-1.5 overflow-y-auto text-sm">
                {data.errors.map((e, i) => (
                  <li key={i} className="flex gap-3 rounded-lg bg-destructive/5 px-3 py-2"><span className="font-mono text-xs text-destructive">Row {e.row}</span><span>{e.error}</span></li>
                ))}
              </ul>
            </Panel>
          )}
        </>
      )}

      {!data && !loading && <Empty title="No file scored yet" hint="Upload a CSV to score many clients at once" />}
    </div>
  );
}
