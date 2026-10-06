import { useQuery } from "@tanstack/react-query";
import { api } from "./api";

// Model artifacts only change when the pipeline is re-run, so fetch each endpoint once per session.
const once = { staleTime: Infinity, retry: false } as const;

export const useMetadata = () => useQuery({ queryKey: ["metadata"], queryFn: api.metadata, ...once });
export const useMetrics = () => useQuery({ queryKey: ["metrics"], queryFn: api.metrics, ...once });
export const useInsights = () => useQuery({ queryKey: ["insights"], queryFn: api.insights, ...once });

/** True when any page-level data came from the built-in mock instead of the backend. */
export function useDemoMode() {
  const queries = [useMetadata(), useMetrics(), useInsights()];
  return queries.some((q) => q.data?.demo);
}
