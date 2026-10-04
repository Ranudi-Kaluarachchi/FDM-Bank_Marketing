// Display information for the 15 model inputs: labels, help text and form grouping.

export interface FieldInfo {
  label: string;   // human-friendly label shown on the form
  help?: string;   // optional hint shown under the input
  group: "Client profile" | "Finances" | "Current campaign" | "Previous campaign";
}

// Keyed by the API field name (same names as the dataset columns).
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

// Order in which the form sections appear.
export const GROUPS: FieldInfo["group"][] = ["Client profile", "Finances", "Current campaign", "Previous campaign"];

// Browser-side input limits; these mirror the backend validation in backend/app/schemas.py.
export const NUMERIC_LIMITS: Record<string, { min: number; max: number }> = {
  age: { min: 18, max: 100 },
  balance: { min: -100000, max: 1000000 },
  day: { min: 1, max: 31 },
  campaign: { min: 1, max: 100 },
  pdays: { min: -1, max: 1000 },
  previous: { min: 0, max: 300 },
};

// Format a 0-1 number as a percentage string, e.g. pct(0.1234) -> "12.3%".
export const pct = (v: number, digits = 1) => `${(v * 100).toFixed(digits)}%`;
