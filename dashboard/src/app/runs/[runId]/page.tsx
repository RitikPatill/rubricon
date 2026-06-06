import Link from 'next/link'
import { getRun, CriterionScore, ScenarioSummary } from '@/lib/api'
import { notFound } from 'next/navigation'

export const dynamic = 'force-dynamic'

function scoreChipColor(score: number): string {
  if (score >= 4) return 'bg-green-100 text-green-800'
  if (score >= 3) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

function overallBadgeColor(score: number | null): string {
  if (score === null) return 'bg-gray-100 text-gray-600'
  if (score >= 3.5) return 'bg-green-100 text-green-800'
  if (score >= 2.5) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

export default async function RunDetailPage({
  params,
}: {
  params: { runId: string }
}) {
  let run
  try {
    run = await getRun(params.runId)
  } catch {
    notFound()
  }

  return (
    <div>
      <Link href="/runs" className="text-blue-600 hover:underline text-sm mb-4 inline-block">
        ← Back to Runs
      </Link>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">{run.suite_name}</h1>
        <div className="flex items-center gap-3 mt-2 text-sm text-gray-600">
          <span className="font-mono text-xs">{run.id}</span>
          <span
            className={`px-2 py-0.5 rounded font-medium ${overallBadgeColor(run.overall_score)}`}
          >
            {run.overall_score !== null
              ? `${run.overall_score.toFixed(2)}/5`
              : 'no score'}
          </span>
          <span>Started: {new Date(run.started_at).toLocaleString()}</span>
          {run.finished_at && (
            <span>Finished: {new Date(run.finished_at).toLocaleString()}</span>
          )}
        </div>
      </div>

      <h2 className="text-lg font-semibold mb-3">Scenarios</h2>
      <div className="grid gap-4">
        {run.scenario_results.map((sr: ScenarioSummary) => (
          <div key={sr.scenario_id} className="bg-white border rounded-lg p-4 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-medium">{sr.scenario_id}</span>
                <span
                  className={`px-2 py-0.5 rounded text-xs font-medium ${
                    sr.status === 'pass'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  {sr.status}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600">
                  {sr.weighted_score !== null
                    ? `${sr.weighted_score.toFixed(2)}/5`
                    : '—'}
                </span>
                <Link
                  href={`/runs/${params.runId}/scenarios/${sr.scenario_id}`}
                  className="text-xs text-blue-600 hover:underline"
                >
                  Timeline →
                </Link>
              </div>
            </div>
            {sr.scores.length > 0 && (
              <div className="space-y-2">
                {sr.scores.map((cs: CriterionScore) => (
                  <div key={cs.criterion_name} className="flex items-start gap-2 text-sm">
                    <span
                      className={`shrink-0 px-1.5 py-0.5 rounded text-xs font-bold ${scoreChipColor(cs.score)}`}
                    >
                      {cs.score}
                    </span>
                    <span
                      className={`shrink-0 w-3 h-3 mt-0.5 rounded-full ${
                        cs.passed ? 'bg-green-500' : 'bg-red-400'
                      }`}
                      title={cs.passed ? 'passed' : 'failed'}
                    />
                    <span className="font-medium text-gray-700">{cs.criterion_name}</span>
                    {cs.cited_span_id ? (
                      <Link
                        href={`/runs/${params.runId}/scenarios/${sr.scenario_id}?highlight=${cs.cited_span_id}`}
                        className="text-gray-500 text-xs leading-relaxed hover:text-blue-700 hover:underline"
                      >
                        {cs.justification}
                      </Link>
                    ) : (
                      <span className="text-gray-500 text-xs leading-relaxed">
                        {cs.justification}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
