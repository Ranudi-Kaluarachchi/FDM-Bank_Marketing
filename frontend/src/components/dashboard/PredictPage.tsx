import { useEffect, useState } from "react";
import { RotateCcw, Sparkles } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Metadata, type Prediction } from "@/lib/api";
import { SECTIONS, pct, type FieldDef } from "@/lib/fields";
import { cn } from "@/lib/utils";
import { LikelihoodBadge, Panel } from "./shared";

type Values = Record<string, string | number>;

export function PredictPage({ meta, onDemo }: { meta: Metadata | null; onDemo: (d: boolean) => void }) {
  const [values, setValues] = useState<Values>(() => ({ ...meta?.defaults }));
  const [result, setResult] = useState<Prediction | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { if (meta) setValues({ ...meta.defaults }); }, [meta]);

  if (!meta) return <div className="grid gap-6 lg:grid-cols-[1fr_360px]"><Skeleton className="h-[640px] rounded-2xl" /><Skeleton className="h-[420px] rounded-2xl" /></div>;

  const set = (k: string, v: string | number) => { setValues((p) => ({ ...p, [k]: v })); };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = Object.fromEntries(meta.features.order.map((k) => [k, meta.features.numeric[k] ? Number(values[k]) : values[k]]));
      const r = await api.predict(payload);
      setResult(r.data);
      onDemo(r.demo);
    } catch { /* toasted */ } finally { setLoading(false); }
  };

  const reset = () => { setValues({ ...meta.defaults }); setResult(null); };

  const renderField = (f: FieldDef) => {
    const v = values[f.name];
    if (f.kind === "toggle") {
      return (
        <div key={f.name} className="flex items-center justify-between rounded-lg border border-border bg-muted/40 px-3 py-2.5">
          <Label htmlFor={f.name} className="font-medium">{f.label}</Label>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {v === "yes" ? "Yes" : "No"}
            <Switch id={f.name} checked={v === "yes"} onCheckedChange={(c) => set(f.name, c ? "yes" : "no")} />
          </div>
        </div>
      );
    }
    if (f.kind === "select") {
      const opts = meta.features.categorical[f.name] ?? [];
      return (
        <div key={f.name} className="space-y-1.5">
          <Label>{f.label}</Label>
          {/* Radix Select can emit "" when its value changes before items register; never let that clear a field. */}
          <Select value={String(v ?? "")} onValueChange={(x) => x && set(f.name, x)}>
            <SelectTrigger><SelectValue placeholder="Select…" /></SelectTrigger>
            <SelectContent>{opts.map((o) => <SelectItem key={o} value={o} className="capitalize">{o}</SelectItem>)}</SelectContent>
          </Select>
          {f.hint && <p className="text-xs text-muted-foreground">{f.hint}</p>}
        </div>
      );
    }
    return (
      <div key={f.name} className="space-y-1.5">
        <Label htmlFor={f.name}>{f.label}{f.prefix && <span className="text-muted-foreground"> ({f.prefix})</span>}</Label>
        <Input id={f.name} type="number" required min={f.min} max={f.max} step={1} value={v ?? ""} onChange={(e) => set(f.name, e.target.value)} />
        <p className="text-xs text-muted-foreground">{f.hint ?? `${f.min} – ${f.max?.toLocaleString()}`}</p>
      </div>
    );
  };

  return (
    <form onSubmit={submit} className="grid gap-6 lg:grid-cols-[1fr_360px]">
      <div className="grid gap-6 md:grid-cols-2">
        {SECTIONS.map((s) => (
          <Panel key={s.title} title={s.title} description={s.description}>
            <div className="grid gap-4">{s.fields.map(renderField)}</div>
          </Panel>
        ))}
      </div>
      <div className="lg:sticky lg:top-6 lg:self-start">
        <Panel title="Prediction" description="Will this client subscribe to a term deposit?">
          <ResultView result={result} threshold={meta.threshold} />
          <div className="mt-6 grid gap-2">
            <Button type="submit" size="lg" disabled={loading}><Sparkles className="mr-2 h-4 w-4" />{loading ? "Scoring…" : "Predict"}</Button>
            <Button type="button" variant="outline" onClick={reset}><RotateCcw className="mr-2 h-4 w-4" />Reset to defaults</Button>
          </div>
        </Panel>
      </div>
    </form>
  );
}

function ResultView({ result, threshold }: { result: Prediction | null; threshold: number }) {
  if (!result) {
    return (
      <div className="rounded-xl border border-dashed border-border py-10 text-center">
        <p className="text-sm font-medium">No prediction yet</p>
        <p className="mt-1 text-xs text-muted-foreground">Fill in the form and press Predict</p>
      </div>
    );
  }
  const yes = result.prediction === "yes";
  const t = result.threshold ?? threshold;
  return (
    <div className="space-y-5">
      <div className={cn("rounded-xl py-6 text-center", yes ? "bg-yes-soft" : "bg-no-soft")}>
        <p className={cn("text-5xl font-extrabold tracking-tight", yes ? "text-yes" : "text-no")}>{yes ? "YES" : "NO"}</p>
        <p className="mt-1 text-sm text-muted-foreground">{yes ? "Likely to subscribe" : "Unlikely to subscribe"}</p>
      </div>
      <div>
        <div className="mb-2 flex items-baseline justify-between">
          <span className="text-sm text-muted-foreground">Probability</span>
          <span className="text-2xl font-bold tabular-nums">{pct(result.probability)}</span>
        </div>
        <div className="relative h-3 rounded-full bg-muted">
          <div className={cn("h-full rounded-full transition-all duration-700", yes ? "bg-yes" : "bg-no")} style={{ width: `${result.probability * 100}%` }} />
          <div className="absolute -top-1.5 h-6 w-0.5 rounded bg-foreground" style={{ left: `${t * 100}%` }} />
        </div>
        <div className="mt-1.5 flex justify-between text-xs text-muted-foreground">
          <span>0%</span><span style={{ marginLeft: `${t * 100 - 15}%` }}>threshold {pct(t)}</span><span>100%</span>
        </div>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">Likelihood</span>
        <LikelihoodBadge value={result.likelihood} />
      </div>
    </div>
  );
}
