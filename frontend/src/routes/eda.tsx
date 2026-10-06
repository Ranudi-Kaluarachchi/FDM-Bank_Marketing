import { createFileRoute } from "@tanstack/react-router";
import { TrendingDown, TrendingUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { InsightsPage } from "@/components/dashboard/InsightsPage";
import { PageHeader } from "@/components/layout/AppShell";
import type { InsightsResponse, RateRow } from "@/lib/api";
import { pct } from "@/lib/fields";
import { useInsights } from "@/lib/queries";

export const Route = createFileRoute("/eda")({
  head: () => ({ meta: [{ title: "EDA · Term Deposit Predictor" }] }),
  component: EdaPage,
});

const FINDING_KEYS: { key: string; label: string }[] = [
  { key: "poutcome", label: "Previous outcome" },
  { key: "month", label: "Contact month" },
  { key: "job", label: "Job" },
  { key: "contact", label: "Contact type" },
];

// Ignore tiny groups so a handful of rows cannot dominate the findings.
const MIN_GROUP = 200;

interface Finding { label: string; value: string; rate: number; count: number; up: boolean }

function findings(data: InsightsResponse): Finding[] {
  const { rate_by, campaign_rate } = data.insights;
  const out: Finding[] = [];
  for (const { key, label } of FINDING_KEYS) {
    const top = (rate_by[key] ?? []).filter((r) => r.count >= MIN_GROUP).sort((a, b) => b.rate - a.rate)[0];
    if (top) out.push({ label, value: top.category, rate: top.rate, count: top.count, up: true });
  }
  const last: RateRow | undefined = campaign_rate[campaign_rate.length - 1];
  if (last) out.push({ label: "Calls this campaign", value: last.category, rate: last.rate, count: last.count, up: false });
  return out;
}

function EdaPage() {
  const data = useInsights().data?.data ?? null;
  const overall = data?.insights.class_balance.positive_rate;

  return (
    <div>
      <PageHeader
        title="Exploratory data analysis"
        description="What the UCI Bank Marketing data tells us before any modelling: how imbalanced the target is, how the data was cleaned, and which client groups subscribe most often."
      />

      {data && overall != null && (
        <section className="mb-6">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">Key findings</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {findings(data).map((f) => (
              <Card key={f.label} className="card-soft border-border/70">
                <CardContent className="p-5">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium">{f.label}: <span className="capitalize">{f.value}</span></p>
                    {f.up ? <TrendingUp className="h-4 w-4 text-yes" /> : <TrendingDown className="h-4 w-4 text-destructive" />}
                  </div>
                  <p className={`mt-2 text-2xl font-bold tabular-nums ${f.up ? "text-yes" : "text-destructive"}`}>{pct(f.rate)}</p>
                  <p className="text-xs text-muted-foreground">
                    subscribe · {(f.rate / overall).toFixed(1)}× the {pct(overall)} average · {f.count.toLocaleString()} clients
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}

      <InsightsPage data={data} />
    </div>
  );
}
