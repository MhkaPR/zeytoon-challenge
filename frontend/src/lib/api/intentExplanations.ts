export type IntentDirection = "positive" | "negative";

export interface IntentConfidence {
  lift: number;
  p: number;
  mcc: number;
}

export interface ClusterIntentExplanation {
  cluster_id: number;
  representative_plan_id: number | null;
  plan_ids: number[];
  intent: string;
  direction: IntentDirection | null;
  message: string;
  confidence: IntentConfidence | null;
}
