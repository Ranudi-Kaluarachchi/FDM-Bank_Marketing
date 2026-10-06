import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { BarChart3, Home, Landmark, LineChart, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { pct } from "@/lib/fields";
import { useDemoMode, useMetadata } from "@/lib/queries";

const NAV = [
  { to: "/", label: "Home", icon: Home },
  { to: "/eda", label: "EDA", icon: BarChart3 },
  { to: "/predict", label: "Prediction", icon: Sparkles },
  { to: "/models", label: "Models", icon: LineChart },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const meta = useMetadata().data?.data;
  const isDemo = useDemoMode();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-border bg-card/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="rounded-xl bg-primary p-2 text-primary-foreground"><Landmark className="h-5 w-5" /></div>
            <div className="leading-tight">
              <p className="text-sm font-bold tracking-tight sm:text-base">Term Deposit Predictor</p>
              <p className="hidden text-xs text-muted-foreground sm:block">UCI Bank Marketing</p>
            </div>
          </Link>

          <nav className="order-last flex w-full gap-1 overflow-x-auto rounded-xl bg-muted p-1 md:order-none md:w-auto">
            {NAV.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                activeOptions={{ exact: to === "/" }}
                className="flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
                activeProps={{ className: "bg-card text-foreground shadow-sm" }}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            {isDemo && <Badge variant="outline" className="border-medium/40 bg-medium-soft text-medium">Demo data</Badge>}
            {meta ? (
              <div className="hidden items-center gap-2 rounded-full border border-border bg-secondary px-3 py-1.5 text-xs lg:flex">
                <span className="h-2 w-2 rounded-full bg-yes" />
                <span className="font-semibold">{meta.model_name}</span>
                <span className="text-muted-foreground">·</span>
                <span className="tabular-nums">ROC-AUC {pct(meta.test_metrics.roc_auc)}</span>
              </div>
            ) : <Skeleton className="hidden h-7 w-48 rounded-full lg:block" />}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6">{children}</main>
    </div>
  );
}

/** Page title block used at the top of every route. */
export function PageHeader({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{title}</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>
      </div>
      {action}
    </div>
  );
}
