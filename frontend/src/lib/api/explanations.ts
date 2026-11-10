export type ReasonType = "numeric" | "categorical" | "textual";

export interface Reason {
  feature: string;
  type: ReasonType;
  f1: number;
  unit?: string | null;
  label?: string | null;
  real_range?: [number, number];
}

export interface ClusterExplanation {
  cluster_id: number;
  representative_plan_id: number | null;
  reasons: Reason[];
}
