import Link from 'next/link'
import { getSuites, SuiteSummary } from '@/lib/api'

export const dynamic = 'force-dynamic'

export default async function SuitesPage() {
  const suites = await getSuites()

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Suites</h1>
      {suites.length === 0 ? (
        <p className="text-gray-500">
          No suites yet. Run a suite with{' '}
          <code className="bg-gray-100 px-1 rounded">rubricon run &lt;suite.yaml&gt;</code>.
        </p>
      ) : (
        <div className="grid gap-4">
          {suites.map((suite: SuiteSummary) => (
            <div key={suite.id} className="bg-white border rounded-lg p-4 shadow-sm">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="font-semibold text-lg">{suite.name}</h2>
                  {suite.description && (
                    <p className="text-gray-600 text-sm mt-1">{suite.description}</p>
                  )}
                  <p className="text-gray-400 text-xs mt-2">
                    Created: {new Date(suite.created_at).toLocaleString()}
                  </p>
                </div>
                <Link
                  href={`/runs?suite_id=${suite.id}`}
                  className="shrink-0 text-sm text-blue-600 hover:underline ml-4"
                >
                  View runs →
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
