const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface SuiteSummary {
  id: string;
  name: string;
  description: string;
  created_at: string;
}

export interface RunSummary {
  id: string;
  suite_id: string;
  suite_name: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  overall_score: number | null;
}

export interface CriterionScore {
  criterion_name: string;
  score: number;
  justification: string;
  cited_span_id: string | null;
  passed: boolean;
}

export interface ScenarioSummary {
  scenario_id: string;
  status: string;
  weighted_score: number | null;
  scores: CriterionScore[];
}

export interface RunDetail {
  id: string;
  suite_name: string;
  started_at: string;
  finished_at: string | null;
  overall_score: number | null;
  scenario_results: ScenarioSummary[];
}

export interface Span {
  id: string;
  type: string;
  started_at: string;
  ended_at: string;
  data: Record<string, unknown>;
}

export interface TrajectoryOut {
  spans: Span[];
  final_output: string | null;
}

export interface CriterionDiff {
  criterion_name: string;
  score_a: number | null;
  score_b: number | null;
  delta: number | null;
  passed_a: boolean | null;
  passed_b: boolean | null;
}

export interface ScenarioDiff {
  scenario_id: string;
  score_a: number | null;
  score_b: number | null;
  delta: number | null;
  status_a: string;
  status_b: string;
  criteria: CriterionDiff[];
}

export interface RunCompareResult {
  run_a: RunSummary;
  run_b: RunSummary;
  overall_delta: number | null;
  scenarios: ScenarioDiff[];
}

export async function getSuites(): Promise<SuiteSummary[]> {
  const res = await fetch(`${BASE}/suites`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch suites: ${res.status}`);
  return res.json();
}

export async function getRuns(suiteId?: string): Promise<RunSummary[]> {
  const url = suiteId ? `${BASE}/runs?suite_id=${suiteId}` : `${BASE}/runs`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch runs: ${res.status}`);
  return res.json();
}

export async function getRun(runId: string): Promise<RunDetail> {
  const res = await fetch(`${BASE}/runs/${runId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch run ${runId}: ${res.status}`);
  return res.json();
}

export async function getComparison(runA: string, runB: string): Promise<RunCompareResult> {
  const res = await fetch(`${BASE}/compare?run_a=${runA}&run_b=${runB}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`compare fetch failed: ${res.status}`);
  return res.json();
}

export async function getTrajectory(
  runId: string,
  scenarioId: string
): Promise<TrajectoryOut> {
  const res = await fetch(
    `${BASE}/runs/${runId}/scenarios/${scenarioId}/trajectory`,
    { cache: "no-store" }
  );
  if (!res.ok)
    throw new Error(`Failed to fetch trajectory: ${res.status}`);
  return res.json();
}
