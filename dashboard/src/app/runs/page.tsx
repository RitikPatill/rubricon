import Link from 'next/link'
import { getRuns, RunSummary } from '@/lib/api'

export const dynamic = 'force-dynamic'

function scoreColor(score: number | null): string {
  if (score === null) return 'bg-gray-100 text-gray-600'
  if (score >= 3.5) return 'bg-green-100 text-green-800'
  if (score >= 2.5) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

export default async function RunsPage({
  searchParams,
}: {
  searchParams: { suite_id?: string | string[] }
}) {
  const suiteId =
    typeof searchParams.suite_id === 'string' ? searchParams.suite_id : undefined
  const runs = await getRuns(suiteId)

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Runs</h1>
      {runs.length === 0 ? (
        <p className="text-gray-500">No runs yet. Run a suite with <code className="bg-gray-100 px-1 rounded">rubricon run &lt;suite.yaml&gt;</code>.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b text-left text-gray-600">
                <th className="py-2 pr-4">Run ID</th>
                <th className="py-2 pr-4">Suite</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Score</th>
                <th className="py-2">Started At</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run: RunSummary) => (
                <tr key={run.id} className="border-b hover:bg-gray-50">
                  <td className="py-2 pr-4 font-mono">
                    <Link
                      href={`/runs/${run.id}`}
                      className="text-blue-600 hover:underline"
                    >
                      {run.id.slice(0, 12)}…
                    </Link>
                  </td>
                  <td className="py-2 pr-4">{run.suite_name}</td>
                  <td className="py-2 pr-4">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        run.status === 'completed'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {run.status}
                    </span>
                  </td>
                  <td className="py-2 pr-4">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${scoreColor(run.overall_score)}`}
                    >
                      {run.overall_score !== null
                        ? `${run.overall_score.toFixed(2)}/5`
                        : '—'}
                    </span>
                  </td>
                  <td className="py-2 text-gray-500">
                    {new Date(run.started_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
