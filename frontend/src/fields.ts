export interface FieldInfo {
  label: string;
  help?: string;
  group: "Client profile" | "Finances" | "Current campaign" | "Previous campaign";
}

export const FIELDS: Record<string, FieldInfo> = {
  age: { label: "Age", group: "Client profile" },
  job: { label: "Job", group: "Client profile" },
  marital: { label: "Marital status", help: "'divorced' includes widowed", group: "Client profile" },
  education: { label: "Education", group: "Client profile" },
  default: { label: "Credit in default?", group: "Finances" },
  balance: { label: "Average yearly balance (€)", group: "Finances" },
  housing: { label: "Housing loan?", group: "Finances" },
  loan: { label: "Personal loan?", group: "Finances" },
  contact: { label: "Contact type", group: "Current campaign" },
  day: { label: "Last contact day of month", group: "Current campaign" },
  month: { label: "Last contact month", group: "Current campaign" },
  campaign: { label: "Contacts this campaign", help: "Including the last contact", group: "Current campaign" },
  pdays: { label: "Days since previous contact", help: "-1 = never contacted before", group: "Previous campaign" },
  previous: { label: "Contacts before this campaign", group: "Previous campaign" },
  poutcome: { label: "Previous campaign outcome", group: "Previous campaign" },
};

export const GROUPS: FieldInfo["group"][] = ["Client profile", "Finances", "Current campaign", "Previous campaign"];

export const NUMERIC_LIMITS: Record<string, { min: number; max: number }> = {
  age: { min: 18, max: 100 },
  balance: { min: -100000, max: 1000000 },
  day: { min: 1, max: 31 },
  campaign: { min: 1, max: 100 },
  pdays: { min: -1, max: 1000 },
  previous: { min: 0, max: 300 },
};

export const pct = (v: number, digits = 1) => `${(v * 100).toFixed(digits)}%`;
