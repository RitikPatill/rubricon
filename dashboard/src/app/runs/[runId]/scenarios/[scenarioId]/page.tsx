import Link from 'next/link'
import { getRun, getTrajectory } from '@/lib/api'
import { notFound } from 'next/navigation'
import ScenarioDetailClient from '@/components/ScenarioDetailClient'

export const dynamic = 'force-dynamic'

export default async function ScenarioDetailPage({
  params,
  searchParams,
}: {
  params: { runId: string; scenarioId: string }
  searchParams: { highlight?: string }
}) {
  const { runId, scenarioId } = params
  const initialHighlight = searchParams.highlight ?? null

  let run, trajectory
  try {
    ;[run, trajectory] = await Promise.all([
      getRun(runId),
      getTrajectory(runId, scenarioId),
    ])
  } catch {
    notFound()
  }

  const scenarioResult = run.scenario_results.find(
    (sr) => sr.scenario_id === scenarioId
  )
  if (!scenarioResult) notFound()

  return (
    <div>
      <Link
        href={`/runs/${runId}`}
        className="text-blue-600 hover:underline text-sm mb-4 inline-block"
      >
        ← Back to Run
      </Link>
      <div className="mb-6">
        <h1 className="text-2xl font-bold font-mono">{scenarioId}</h1>
        <div className="flex items-center gap-3 mt-2 text-sm text-gray-600">
          <span
            className={`px-2 py-0.5 rounded font-medium text-xs ${
              scenarioResult.status === 'pass'
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {scenarioResult.status}
          </span>
          {scenarioResult.weighted_score !== null && (
            <span className="font-medium">
              {scenarioResult.weighted_score.toFixed(2)}/5
            </span>
          )}
        </div>
      </div>

      <ScenarioDetailClient
        scenarioId={scenarioId}
        scores={scenarioResult.scores}
        spans={trajectory.spans}
        finalOutput={trajectory.final_output}
        initialHighlight={initialHighlight}
        runId={runId}
      />
    </div>
  )
}
