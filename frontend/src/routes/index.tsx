import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, BarChart3, Brain, Database, Eraser, LineChart, Server, Sparkles, Target } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Kpi, Panel } from "@/components/dashboard/shared";
import { SECTIONS, pct } from "@/lib/fields";
import { useInsights, useMetadata, useMetrics } from "@/lib/queries";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Term Deposit Subscription Predictor" },
      { name: "description", content: "Predict which bank clients will subscribe to a term deposit, explore the UCI Bank Marketing data and compare models." },
      { property: "og:title", content: "Term Deposit Subscription Predictor" },
      { property: "og:description", content: "ML dashboard for the UCI Bank Marketing dataset: EDA, predictions and model performance." },
    ],
  }),
  component: HomePage,
});

const PAGES = [
  { to: "/eda", title: "Exploratory data analysis", icon: BarChart3, text: "Class balance, cleaning steps and subscription rates by job, month, contact type and previous outcome." },
  { to: "/predict", title: "Prediction", icon: Sparkles, text: "Score one client with the form, or upload a CSV to score a whole call list and download the results." },
  { to: "/models", title: "Model performance", icon: LineChart, text: "Six models compared on the held-out test set: ROC curves, confusion matrix and feature importance." },
] as const;

function HomePage() {
  const meta = useMetadata().data?.data;
  const metrics = useMetrics().data?.data;
  const insights = useInsights().data?.data;
  const tuned = metrics?.best_model_tuned_test;

  const steps = [
    { icon: Database, title: "Data", text: `${insights ? insights.cleaning.raw_rows.toLocaleString() : "45,211"} phone calls from a Portuguese bank's marketing campaigns (2008–2010).` },
    { icon: Eraser, title: "Cleaning", text: `${insights?.cleaning.steps.length ?? 6} steps: normalise text, handle missing values, drop duplicates and the leaky "duration" column.` },
    { icon: Brain, title: "Modelling", text: `${metrics?.models.length ?? 6} classifiers tuned with cross-validation and compared on ROC-AUC.` },
    { icon: Target, title: "Threshold", text: `The winner's decision threshold${meta ? ` (${meta.threshold.toFixed(2)})` : ""} is tuned for F1, because only ~12% of clients subscribe.` },
    { icon: Server, title: "Serving", text: "A FastAPI service validates inputs and serves predictions to this dashboard." },
  ];

  return (
    <div className="space-y-12">
      <section className="grid items-center gap-8 lg:grid-cols-[1.3fr_1fr]">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-5xl">
            Find the clients most likely to open a <span className="text-primary">term deposit</span>
          </h1>
          <p className="mt-4 max-w-xl text-base text-muted-foreground">
            Only about one in nine calls in a bank telemarketing campaign ends in a subscription. This tool predicts each
            client's chance of subscribing, so the call team can phone the most promising leads first.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button asChild size="lg"><Link to="/predict"><Sparkles className="mr-2 h-4 w-4" />Predict a client</Link></Button>
            <Button asChild size="lg" variant="outline"><Link to="/eda"><BarChart3 className="mr-2 h-4 w-4" />Explore the data</Link></Button>
          </div>
        </div>

        <Card className="card-soft border-border/70 bg-primary text-primary-foreground">
          <CardContent className="space-y-5 p-6">
            <p className="text-xs font-medium uppercase tracking-wider opacity-80">Serving model</p>
            <p className="text-3xl font-bold">{meta?.model_name ?? "—"}</p>
            <div className="grid grid-cols-2 gap-4">
              <Stat label="ROC-AUC" value={pct(tuned?.roc_auc)} />
              <Stat label="Recall" value={pct(tuned?.recall)} />
              <Stat label="Precision" value={pct(tuned?.precision)} />
              <Stat label="Threshold" value={meta ? meta.threshold.toFixed(2) : "—"} />
            </div>
            <p className="text-xs opacity-80">
              Trained on {meta ? meta.training_rows.toLocaleString() : "—"} rows
              {meta && ` · ${new Date(meta.trained_at).toLocaleDateString()}`}
            </p>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Calls analysed" value={insights ? insights.insights.rows.toLocaleString() : "—"} />
        <Kpi label="Subscription rate" value={pct(insights?.insights.class_balance.positive_rate)} tone="yes" sub="Heavily imbalanced target" />
        <Kpi label="Models compared" value={metrics?.models.length ?? "—"} />
        <Kpi label="Model inputs" value={SECTIONS.reduce((n, s) => n + s.fields.length, 0)} sub="Client, finances and campaign history" />
      </section>

      <section>
        <h2 className="mb-4 text-xl font-bold tracking-tight">How it works</h2>
        <ol className="grid gap-4 md:grid-cols-5">
          {steps.map(({ icon: Icon, title, text }, i) => (
            <li key={title} className="card-soft rounded-2xl border border-border/70 bg-card p-5">
              <div className="mb-3 flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">{i + 1}</span>
                <Icon className="h-4 w-4 text-primary" />
              </div>
              <p className="font-semibold">{title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-bold tracking-tight">Explore</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {PAGES.map(({ to, title, icon: Icon, text }) => (
            <Link key={to} to={to} className="group">
              <Card className="card-soft h-full border-border/70 transition-all group-hover:-translate-y-0.5 group-hover:border-primary/40">
                <CardContent className="flex h-full flex-col p-6">
                  <div className="mb-4 w-fit rounded-xl bg-accent p-2.5 text-accent-foreground"><Icon className="h-5 w-5" /></div>
                  <p className="font-semibold">{title}</p>
                  <p className="mt-1 flex-1 text-sm text-muted-foreground">{text}</p>
                  <span className="mt-4 flex items-center text-sm font-medium text-primary">
                    Open <ArrowRight className="ml-1 h-4 w-4 transition-transform group-hover:translate-x-1" />
                  </span>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      <Panel title="What the model looks at" description="The 15 inputs used for every prediction. Call duration is excluded because it is only known after the call.">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {SECTIONS.map((s) => (
            <div key={s.title}>
              <p className="text-sm font-semibold">{s.title}</p>
              <p className="mb-2 text-xs text-muted-foreground">{s.description}</p>
              <div className="flex flex-wrap gap-1.5">
                {s.fields.map((f) => <Badge key={f.name} variant="secondary" className="font-normal">{f.label}</Badge>)}
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-primary-foreground/10 p-3">
      <p className="text-xs opacity-80">{label}</p>
      <p className="text-xl font-bold tabular-nums">{value}</p>
    </div>
  );
}
