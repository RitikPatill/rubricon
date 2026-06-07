'use client'

import { useState } from 'react'
import Link from 'next/link'
import { CriterionScore, Span } from '@/lib/api'
import TrajectoryTimeline from './TrajectoryTimeline'

function scoreChipColor(score: number): string {
  if (score >= 4) return 'bg-green-100 text-green-800'
  if (score >= 3) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

interface Props {
  scenarioId: string
  runId: string
  scores: CriterionScore[]
  spans: Span[]
  finalOutput: string | null
  initialHighlight: string | null
}

export default function ScenarioDetailClient({
  scenarioId,
  runId,
  scores,
  spans,
  finalOutput,
  initialHighlight,
}: Props) {
  const [highlightedSpanId, setHighlightedSpanId] = useState<string | null>(
    initialHighlight
  )

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left: criterion scores */}
      <div className="sticky top-4 self-start space-y-3">
        <h2 className="text-lg font-semibold">Criteria</h2>
        {scores.length === 0 && (
          <p className="text-gray-500 text-sm">No scores recorded.</p>
        )}
        {scores.map((cs) => (
          <div
            key={cs.criterion_name}
            className="bg-white border rounded-lg p-4 shadow-sm"
          >
            <div className="flex items-center gap-2 mb-2">
              <span
                className={`px-1.5 py-0.5 rounded text-xs font-bold ${scoreChipColor(cs.score)}`}
              >
                {cs.score}
              </span>
              <span
                className={`w-3 h-3 rounded-full shrink-0 ${
                  cs.passed ? 'bg-green-500' : 'bg-red-400'
                }`}
                title={cs.passed ? 'passed' : 'failed'}
              />
              <span className="font-medium text-sm">{cs.criterion_name}</span>
            </div>
            {cs.cited_span_id ? (
              <div className="flex items-start gap-1">
                <button
                  className="text-xs text-gray-600 leading-relaxed text-left hover:text-blue-700 cursor-pointer"
                  onClick={() => setHighlightedSpanId(cs.cited_span_id)}
                >
                  {cs.justification}
                </button>
                <Link
                  href={`/runs/${runId}/scenarios/${scenarioId}?highlight=${cs.cited_span_id}`}
                  className="shrink-0 ml-1 text-gray-400 hover:text-blue-600"
                  title="Copy link to cited span"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="w-3 h-3 mt-0.5"
                  >
                    <path
                      fillRule="evenodd"
                      d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z"
                      clipRule="evenodd"
                    />
                  </svg>
                </Link>
              </div>
            ) : (
              <p className="text-xs text-gray-600 leading-relaxed">
                {cs.justification}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Right: trajectory timeline */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Trajectory</h2>
        <TrajectoryTimeline
          spans={spans}
          finalOutput={finalOutput}
          highlightedSpanId={highlightedSpanId}
        />
      </div>
    </div>
  )
}
