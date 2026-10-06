import { createFileRoute } from "@tanstack/react-router";
import { Database, UserRound } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BatchPage } from "@/components/dashboard/BatchPage";
import { PredictPage } from "@/components/dashboard/PredictPage";
import { PageHeader } from "@/components/layout/AppShell";
import { useMetadata } from "@/lib/queries";

export const Route = createFileRoute("/predict")({
  head: () => ({ meta: [{ title: "Prediction · Term Deposit Predictor" }] }),
  component: PredictionPage,
});

const noop = () => {};

function PredictionPage() {
  const meta = useMetadata().data?.data ?? null;

  return (
    <div>
      <PageHeader
        title="Prediction"
        description="Estimate how likely a client is to subscribe to a term deposit. Score a single client with the form, or upload a CSV to score a whole call list."
      />
      <Tabs defaultValue="single" className="space-y-6">
        <TabsList className="h-auto">
          <TabsTrigger value="single" className="gap-1.5"><UserRound className="h-4 w-4" />Single client</TabsTrigger>
          <TabsTrigger value="batch" className="gap-1.5"><Database className="h-4 w-4" />Batch (CSV)</TabsTrigger>
        </TabsList>
        <TabsContent value="single"><PredictPage meta={meta} onDemo={noop} /></TabsContent>
        <TabsContent value="batch"><BatchPage onDemo={noop} /></TabsContent>
      </Tabs>
    </div>
  );
}
