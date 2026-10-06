import type { ReactNode } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { Likelihood } from "@/lib/api";

export function Panel({ title, description, children, className, action }: { title: string; description?: string; children: ReactNode; className?: string; action?: ReactNode }) {
  return (
    <Card className={cn("card-soft border-border/70", className)}>
      <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
        <div className="space-y-1">
          <CardTitle className="text-base font-semibold">{title}</CardTitle>
          {description && <CardDescription>{description}</CardDescription>}
        </div>
        {action}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export function Kpi({ label, value, tone = "default", sub }: { label: string; value: ReactNode; tone?: "default" | "yes" | "no" | "medium" | "destructive"; sub?: string }) {
  const toneCls = { default: "text-foreground", yes: "text-yes", no: "text-no", medium: "text-medium", destructive: "text-destructive" }[tone];
  return (
    <Card className="card-soft border-border/70">
      <CardContent className="p-5">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
        <p className={cn("mt-2 text-3xl font-bold tabular-nums", toneCls)}>{value}</p>
        {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
      </CardContent>
    </Card>
  );
}

export function LikelihoodBadge({ value }: { value: Likelihood }) {
  const cls = { high: "bg-yes-soft text-yes border-yes/30", medium: "bg-medium-soft text-medium border-medium/40", low: "bg-no-soft text-no border-no/30" }[value];
  return <Badge variant="outline" className={cn("capitalize", cls)}>{value}</Badge>;
}

export function PredictionBadge({ value }: { value: "yes" | "no" }) {
  return (
    <Badge variant="outline" className={cn("uppercase", value === "yes" ? "bg-yes-soft text-yes border-yes/30" : "bg-no-soft text-no border-no/30")}>
      {value}
    </Badge>
  );
}

export function ChartSkeleton({ h = 280 }: { h?: number }) {
  return <Skeleton className="w-full rounded-xl" style={{ height: h }} />;
}

export function Empty({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-12 text-center">
      <p className="text-sm font-medium">{title}</p>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

export const C = {
  primary: "var(--color-primary)",
  yes: "var(--color-yes)",
  no: "var(--color-no)",
  medium: "var(--color-medium)",
  grid: "var(--color-border)",
  muted: "var(--color-muted-foreground)",
  series: ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"],
};

export const tooltipStyle = {
  contentStyle: { background: "var(--color-popover)", border: "1px solid var(--color-border)", borderRadius: 10, fontSize: 12 },
};
