import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { InsightsResponse } from "@/lib/api";
import { pct } from "@/lib/fields";
import { C, ChartSkeleton, Empty, Kpi, Panel, tooltipStyle } from "./shared";

export function InsightsPage({ data }: { data: InsightsResponse | null }) {
  const [key, setKey] = useState("month");
  if (!data) return <div className="grid gap-6 lg:grid-cols-2">{Array.from({ length: 6 }).map((_, i) => <ChartSkeleton key={i} />)}</div>;
  const { insights: ins, cleaning } = data;
  const keys = Object.keys(ins.rate_by);
  const activeKey = keys.includes(key) ? key : keys[0];
  const rateRows = ins.rate_by[activeKey] ?? [];
  const donut = [{ name: "Subscribed (yes)", value: ins.class_balance.yes }, { name: "Not subscribed (no)", value: ins.class_balance.no }];
  const corr = Object.entries(ins.numeric_correlation_with_target).map(([feature, value]) => ({ feature, value })).sort((a, b) => b.value - a.value);
  const rateAxis = { tickFormatter: (v: number) => `${Math.round(v * 100)}%`, tick: { fontSize: 12, fill: C.muted } };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Kpi label="Raw rows" value={cleaning.raw_rows.toLocaleString()} />
        <Kpi label="Clean rows" value={cleaning.clean_rows.toLocaleString()} sub={`${(cleaning.raw_rows - cleaning.clean_rows).toLocaleString()} removed`} />
        <Kpi label="Subscription rate" value={pct(cleaning.positive_rate)} tone="yes" />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
        <Panel title="Class balance" description="Target is heavily imbalanced">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={donut} dataKey="value" innerRadius={65} outerRadius={100} paddingAngle={2} stroke="none">
                <Cell fill={C.yes} /><Cell fill={C.no} />
              </Pie>
              <Tooltip {...tooltipStyle} formatter={(v: number) => `${v.toLocaleString()} (${pct(v / ins.rows)})`} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Data cleaning steps">
          {cleaning.steps.length === 0 ? <Empty title="No cleaning steps recorded" /> : (
            <ol className="relative space-y-4 border-l-2 border-border pl-6">
              {cleaning.steps.map((s, i) => (
                <li key={i} className="relative">
                  <span className="absolute -left-[33px] flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">{i + 1}</span>
                  <p className="text-sm font-medium">{s.step}</p>
                  {s.detail && <p className="text-xs text-muted-foreground">{s.detail}</p>}
                  {s.rows_removed != null && <p className="text-xs text-medium">{s.rows_removed.toLocaleString()} rows removed</p>}
                </li>
              ))}
            </ol>
          )}
        </Panel>
      </div>

      <Panel
        title="Subscription rate by category"
        description={`Dashed line = overall rate ${pct(ins.class_balance.positive_rate)}`}
        action={
          <Select value={activeKey} onValueChange={setKey}>
            <SelectTrigger className="w-40 capitalize"><SelectValue /></SelectTrigger>
            <SelectContent>{keys.map((k) => <SelectItem key={k} value={k} className="capitalize">{k}</SelectItem>)}</SelectContent>
          </Select>
        }
      >
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={rateRows}>
            <CartesianGrid strokeDasharray="3 3" stroke={C.grid} vertical={false} />
            <XAxis dataKey="category" tick={{ fontSize: 12, fill: C.muted }} interval={0} angle={rateRows.length > 8 ? -30 : 0} textAnchor={rateRows.length > 8 ? "end" : "middle"} height={rateRows.length > 8 ? 60 : 30} />
            <YAxis {...rateAxis} />
            <Tooltip {...tooltipStyle} formatter={(v: number, _n, p) => [`${pct(v)} of ${p.payload.count.toLocaleString()}`, "Rate"]} />
            <ReferenceLine y={ins.class_balance.positive_rate} stroke={C.medium} strokeDasharray="5 5" />
            <Bar dataKey="rate" fill={C.primary} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Age distribution" description="Clients by age band and outcome">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={ins.age_histogram}>
              <CartesianGrid strokeDasharray="3 3" stroke={C.grid} vertical={false} />
              <XAxis dataKey="bin" tick={{ fontSize: 11, fill: C.muted }} />
              <YAxis tick={{ fontSize: 12, fill: C.muted }} />
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="no" stackId="a" fill={C.no} name="No" />
              <Bar dataKey="yes" stackId="a" fill={C.yes} name="Yes" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Rate by number of campaign calls" description="More calls, fewer subscriptions">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={ins.campaign_rate}>
              <CartesianGrid strokeDasharray="3 3" stroke={C.grid} vertical={false} />
              <XAxis dataKey="category" tick={{ fontSize: 12, fill: C.muted }} />
              <YAxis {...rateAxis} />
              <Tooltip {...tooltipStyle} formatter={(v: number, _n, p) => [`${pct(v)} of ${p.payload.count.toLocaleString()}`, "Rate"]} />
              <Bar dataKey="rate" fill={C.medium} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
      </div>

      <Panel title="Correlation with subscription" description="Pearson correlation of numeric features with the target">
        <ResponsiveContainer width="100%" height={Math.max(220, corr.length * 36)}>
          <BarChart data={corr} layout="vertical" margin={{ left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={C.grid} horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 12, fill: C.muted }} tickFormatter={(v) => v.toFixed(2)} />
            <YAxis type="category" dataKey="feature" width={80} tick={{ fontSize: 12, fill: C.muted }} />
            <ReferenceLine x={0} stroke={C.muted} />
            <Tooltip {...tooltipStyle} formatter={(v: number) => v.toFixed(3)} />
            <Bar dataKey="value" radius={4}>{corr.map((c) => <Cell key={c.feature} fill={c.value >= 0 ? C.yes : "var(--color-destructive)"} />)}</Bar>
          </BarChart>
        </ResponsiveContainer>
      </Panel>
    </div>
  );
}
