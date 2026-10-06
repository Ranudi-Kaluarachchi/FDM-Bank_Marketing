import { createFileRoute } from "@tanstack/react-router";
import { PerformancePage } from "@/components/dashboard/PerformancePage";
import { PageHeader } from "@/components/layout/AppShell";
import { useMetrics } from "@/lib/queries";

export const Route = createFileRoute("/models")({
  head: () => ({ meta: [{ title: "Models · Term Deposit Predictor" }] }),
  component: ModelsPage,
});

function ModelsPage() {
  const data = useMetrics().data?.data ?? null;

  return (
    <div>
      <PageHeader
        title="Model performance"
        description="Six classifiers tuned with cross-validation and scored on a held-out test set. The best model by ROC-AUC is the one serving predictions."
      />
      <PerformancePage data={data} />
    </div>
  );
}
