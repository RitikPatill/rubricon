'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import type { RunSummary } from '@/lib/api'

function scoreColor(score: number | null): string {
  if (score === null) return 'bg-gray-100 text-gray-600'
  if (score >= 3.5) return 'bg-green-100 text-green-800'
  if (score >= 2.5) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

export default function RunsListClient({ runs }: { runs: RunSummary[] }) {
  const router = useRouter()
  const [selected, setSelected] = useState<Set<string>>(new Set())

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        if (next.size < 2) next.add(id)
      }
      return next
    })
  }

  if (runs.length === 0) {
    return (
      <p className="text-gray-500">
        No runs yet. Run a suite with{' '}
        <code className="bg-gray-100 px-1 rounded">rubricon run &lt;suite.yaml&gt;</code>.
      </p>
    )
  }

  const selectedArr = Array.from(selected)

  return (
    <>
      {selected.size === 2 && (
        <p className="text-xs text-gray-500 mb-2">2 runs selected — click Compare to diff them.</p>
      )}
      {selected.size === 1 && (
        <p className="text-xs text-gray-500 mb-2">Select one more run to compare.</p>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b text-left text-gray-600">
              <th className="py-2 pr-2 w-8"></th>
              <th className="py-2 pr-4">Run ID</th>
              <th className="py-2 pr-4">Suite</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">Score</th>
              <th className="py-2">Started At</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run: RunSummary) => (
              <tr
                key={run.id}
                className={`border-b hover:bg-gray-50 ${selected.has(run.id) ? 'bg-blue-50' : ''}`}
              >
                <td className="py-2 pr-2">
                  <input
                    type="checkbox"
                    checked={selected.has(run.id)}
                    onChange={() => toggleSelect(run.id)}
                    disabled={selected.size >= 2 && !selected.has(run.id)}
                    className="cursor-pointer"
                    aria-label={`Select run ${run.id}`}
                  />
                </td>
                <td className="py-2 pr-4 font-mono">
                  <Link href={`/runs/${run.id}`} className="text-blue-600 hover:underline">
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
                    {run.overall_score !== null ? `${run.overall_score.toFixed(2)}/5` : '—'}
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

      {selected.size === 2 && (
        <button
          onClick={() =>
            router.push(`/compare?run_a=${selectedArr[0]}&run_b=${selectedArr[1]}`)
          }
          className="fixed bottom-6 right-6 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-5 py-3 rounded-lg shadow-lg transition-colors"
        >
          Compare selected runs →
        </button>
      )}
    </>
  )
}
