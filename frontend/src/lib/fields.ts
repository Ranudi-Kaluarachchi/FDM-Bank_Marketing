export type FieldKind = "number" | "select" | "toggle";

export interface FieldDef {
  name: string;
  label: string;
  kind: FieldKind;
  min?: number;
  max?: number;
  hint?: string;
  prefix?: string;
}

export interface SectionDef {
  title: string;
  description: string;
  fields: FieldDef[];
}

export const SECTIONS: SectionDef[] = [
  {
    title: "Client profile",
    description: "Who the client is",
    fields: [
      { name: "age", label: "Age", kind: "number", min: 18, max: 100 },
      { name: "job", label: "Job", kind: "select" },
      { name: "marital", label: "Marital status", kind: "select", hint: '"divorced" includes widowed' },
      { name: "education", label: "Education", kind: "select" },
    ],
  },
  {
    title: "Finances",
    description: "Credit and balance",
    fields: [
      { name: "default", label: "Credit in default", kind: "toggle" },
      { name: "balance", label: "Average yearly balance", kind: "number", min: -100000, max: 1000000, prefix: "€" },
      { name: "housing", label: "Housing loan", kind: "toggle" },
      { name: "loan", label: "Personal loan", kind: "toggle" },
    ],
  },
  {
    title: "Current campaign",
    description: "Last contact in this campaign",
    fields: [
      { name: "contact", label: "Contact type", kind: "select" },
      { name: "day", label: "Day of month", kind: "number", min: 1, max: 31 },
      { name: "month", label: "Month", kind: "select" },
      { name: "campaign", label: "Contacts this campaign", kind: "number", min: 1, max: 100, hint: "Including last contact" },
    ],
  },
  {
    title: "Previous campaign",
    description: "History with earlier campaigns",
    fields: [
      { name: "pdays", label: "Days since last contact", kind: "number", min: -1, max: 1000, hint: "-1 = never contacted" },
      { name: "previous", label: "Previous contacts", kind: "number", min: 0, max: 300 },
      { name: "poutcome", label: "Previous outcome", kind: "select" },
    ],
  },
];

export const ALL_FIELDS = SECTIONS.flatMap((s) => s.fields);

export const pct = (v: number | null | undefined) =>
  v == null || Number.isNaN(v) ? "—" : `${(v * 100).toFixed(1)}%`;

export const LABELS: Record<string, string> = {
  accuracy: "Accuracy",
  precision: "Precision",
  recall: "Recall",
  f1: "F1",
  roc_auc: "ROC-AUC",
  pr_auc: "PR-AUC",
};
