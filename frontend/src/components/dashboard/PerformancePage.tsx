import { Bar, BarChart, CartesianGrid, ErrorBar, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { MetricsResponse } from "@/lib/api";
import { LABELS, pct } from "@/lib/fields";
import { cn } from "@/lib/utils";
import { C, ChartSkeleton, Panel, tooltipStyle } from "./shared";

const KEYS = ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"] as const;

export function PerformancePage({ data }: { data: MetricsResponse | null }) {
  if (!data) return <div className="grid gap-6 lg:grid-cols-2">{Array.from({ length: 4 }).map((_, i) => <ChartSkeleton key={i} h={340} />)}</div>;

  const grouped = KEYS.map((k) => ({ metric: LABELS[k], ...Object.fromEntries(data.models.map((m) => [m.name, m.test[k]])) }));
  const rocData = Array.from({ length: 21 }, (_, i) => {
    const fpr = i / 20;
    const row: Record<string, number> = { fpr, Chance: fpr };
    data.models.forEach((m) => {
      const pt = m.roc_curve.reduce((best, p) => (Math.abs(p.fpr - fpr) < Math.abs(best.fpr - fpr) ? p : best), m.roc_curve[0]);
      row[m.name] = pt?.tpr ?? 0;
    });
    return row;
  });
  const cm = data.best_model_tuned_test.confusion_matrix;
  const fi = [...data.feature_importance].sort((a, b) => b.importance - a.importance).map((f) => ({ ...f, err: f.std }));

  return (
    <div className="space-y-6">
      <Panel title="Model comparison" description="Held-out test set scores. Best model highlighted.">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow>
              <TableHead>Model</TableHead><TableHead className="text-right">CV ROC-AUC</TableHead>
              {KEYS.map((k) => <TableHead key={k} className="text-right">{LABELS[k]}</TableHead>)}
              <TableHead className="text-right">Train time</TableHead>
            </TableRow></TableHeader>
            <TableBody>{data.models.map((m) => {
              const best = m.name === data.best_model;
              return (
                <TableRow key={m.name} className={cn(best && "bg-accent/60 hover:bg-accent")}>
                  <TableCell className="font-medium">{m.name}{best && <Badge className="ml-2">Best</Badge>}</TableCell>
                  <TableCell className="text-right tabular-nums">{pct(m.cv_roc_auc)}</TableCell>
                  {KEYS.map((k) => <TableCell key={k} className="text-right tabular-nums">{pct(m.test[k])}</TableCell>)}
                  <TableCell className="text-right tabular-nums text-muted-foreground">{m.train_seconds.toFixed(1)}s</TableCell>
                </TableRow>
              );
            })}</TableBody>
          </Table>
        </div>
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Test scores by model">
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={grouped}>
              <CartesianGrid strokeDasharray="3 3" stroke={C.grid} vertical={false} />
              <XAxis dataKey="metric" tick={{ fontSize: 12, fill: C.muted }} />
              <YAxis domain={[0, 1]} tickFormatter={(v) => `${v * 100}%`} tick={{ fontSize: 12, fill: C.muted }} />
              <Tooltip {...tooltipStyle} formatter={(v: number) => pct(v)} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {data.models.map((m, i) => <Bar key={m.name} dataKey={m.name} fill={C.series[i % 5]} radius={[4, 4, 0, 0]} />)}
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="ROC curves" description="True vs false positive rate">
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={rocData}>
              <CartesianGrid strokeDasharray="3 3" stroke={C.grid} />
              <XAxis dataKey="fpr" type="number" domain={[0, 1]} tickFormatter={(v) => v.toFixed(1)} tick={{ fontSize: 12, fill: C.muted }} label={{ value: "FPR", position: "insideBottom", offset: -2, fontSize: 11 }} />
              <YAxis domain={[0, 1]} tickFormatter={(v) => v.toFixed(1)} tick={{ fontSize: 12, fill: C.muted }} />
              <Tooltip {...tooltipStyle} formatter={(v: number) => pct(v)} labelFormatter={(l) => `FPR ${pct(Number(l))}`} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line dataKey="Chance" stroke={C.muted} strokeDasharray="5 5" dot={false} />
              {data.models.map((m, i) => <Line key={m.name} dataKey={m.name} stroke={C.series[i % 5]} strokeWidth={m.name === data.best_model ? 3 : 1.75} dot={false} />)}
            </LineChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Confusion matrix" description={`${data.best_model} at threshold ${pct(data.threshold)}`}>
          {cm ? <ConfusionMatrix cm={cm} /> : <p className="text-sm text-muted-foreground">Not available</p>}
        </Panel>

        <Panel title="Feature importance" description="Permutation importance (± std)">
          <ResponsiveContainer width="100%" height={Math.max(260, fi.length * 24)}>
            <BarChart data={fi} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={C.grid} horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 12, fill: C.muted }} />
              <YAxis type="category" dataKey="feature" width={80} tick={{ fontSize: 12, fill: C.muted }} />
              <Tooltip {...tooltipStyle} formatter={(v: number) => v.toFixed(4)} />
              <Bar dataKey="importance" fill={C.primary} radius={[0, 4, 4, 0]}><ErrorBar dataKey="err" width={4} stroke={C.muted} direction="x" /></Bar>
            </BarChart>
          </ResponsiveContainer>
        </Panel>
      </div>
    </div>
  );
}

function ConfusionMatrix({ cm }: { cm: { tn: number; fp: number; fn: number; tp: number } }) {
  const max = Math.max(cm.tn, cm.fp, cm.fn, cm.tp);
  const total = cm.tn + cm.fp + cm.fn + cm.tp;
  const cell = (v: number, label: string, good: boolean) => (
    <div className="relative flex aspect-[4/3] flex-col items-center justify-center overflow-hidden rounded-xl border border-border">
      <div className={cn("absolute inset-0", good ? "bg-yes" : "bg-destructive")} style={{ opacity: 0.08 + (v / max) * 0.55 }} />
      <span className="relative text-2xl font-bold tabular-nums">{v.toLocaleString()}</span>
      <span className="relative text-xs text-muted-foreground">{label} · {pct(v / total)}</span>
    </div>
  );
  return (
    <div className="grid grid-cols-[auto_1fr_1fr] gap-2 text-sm">
      <div /><div className="text-center text-xs font-medium text-muted-foreground">Predicted no</div><div className="text-center text-xs font-medium text-muted-foreground">Predicted yes</div>
      <div className="flex items-center pr-2 text-xs font-medium text-muted-foreground">Actual no</div>{cell(cm.tn, "True negative", true)}{cell(cm.fp, "False positive", false)}
      <div className="flex items-center pr-2 text-xs font-medium text-muted-foreground">Actual yes</div>{cell(cm.fn, "False negative", false)}{cell(cm.tp, "True positive", true)}
    </div>
  );
}
