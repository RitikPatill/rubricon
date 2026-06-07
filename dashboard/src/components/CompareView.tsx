'use client'

import { useState } from 'react'
import type { RunCompareResult, ScenarioDiff, CriterionDiff } from '@/lib/api'

function deltaChip(delta: number | null) {
  if (delta === null) return <span className="text-gray-400">—</span>
  if (delta > 0.1)
    return (
      <span className="px-2 py-0.5 rounded text-xs font-semibold bg-green-100 text-green-800">
        +{delta.toFixed(2)}
      </span>
    )
  if (delta < -0.1)
    return (
      <span className="px-2 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-800">
        {delta.toFixed(2)}
      </span>
    )
  return (
    <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
      {delta > 0 ? '+' : ''}{delta.toFixed(2)}
    </span>
  )
}

function scoreCell(score: number | null) {
  if (score === null) return <span className="text-gray-400 italic">missing</span>
  return <span>{score.toFixed(2)}</span>
}

function passCell(passed: boolean | null) {
  if (passed === null) return <span className="text-gray-400">—</span>
  return passed ? (
    <span className="text-green-600 font-medium">✓</span>
  ) : (
    <span className="text-red-600 font-medium">✗</span>
  )
}

function rowBg(delta: number | null) {
  if (delta === null) return ''
  if (delta > 0.1) return 'bg-green-50'
  if (delta < -0.1) return 'bg-red-50'
  return ''
}

function CriterionRows({ criteria }: { criteria: CriterionDiff[] }) {
  return (
    <>
      {criteria.map((c) => (
        <tr key={c.criterion_name} className={`border-b text-xs text-gray-600 ${rowBg(c.delta)}`}>
          <td className="py-1.5 pl-8 pr-4 italic">{c.criterion_name}</td>
          <td className="py-1.5 pr-4 text-right">{scoreCell(c.score_a)}</td>
          <td className="py-1.5 pr-4 text-right">{scoreCell(c.score_b)}</td>
          <td className="py-1.5 pr-4 text-right">{deltaChip(c.delta)}</td>
          <td className="py-1.5 pr-4 text-center">{passCell(c.passed_a)}</td>
          <td className="py-1.5 text-center">{passCell(c.passed_b)}</td>
        </tr>
      ))}
    </>
  )
}

export default function CompareView({ data }: { data: RunCompareResult }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const { run_a, run_b, overall_delta, scenarios } = data

  return (
    <div className="space-y-6">
      {/* Header strip */}
      <div className="flex items-center gap-6 p-4 bg-gray-50 rounded-lg border text-sm">
        <div className="flex-1">
          <p className="text-xs text-gray-500 mb-0.5">Run A (baseline)</p>
          <p className="font-mono font-semibold text-gray-800">{run_a.id.slice(0, 12)}…</p>
          <p className="text-gray-600">
            {run_a.overall_score !== null ? `${run_a.overall_score.toFixed(2)}/5` : '—'}
          </p>
        </div>
        <div className="text-2xl text-gray-300">→</div>
        <div className="flex-1">
          <p className="text-xs text-gray-500 mb-0.5">Run B (new)</p>
          <p className="font-mono font-semibold text-gray-800">{run_b.id.slice(0, 12)}…</p>
          <p className="text-gray-600">
            {run_b.overall_score !== null ? `${run_b.overall_score.toFixed(2)}/5` : '—'}
          </p>
        </div>
        <div className="flex flex-col items-center">
          <p className="text-xs text-gray-500 mb-1">Overall Δ</p>
          <div className="text-base">{deltaChip(overall_delta)}</div>
        </div>
      </div>

      {/* Scenario table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b text-left text-gray-600 text-xs">
              <th className="py-2 pr-4">Scenario</th>
              <th className="py-2 pr-4 text-right">Score A</th>
              <th className="py-2 pr-4 text-right">Score B</th>
              <th className="py-2 pr-4 text-right">Δ</th>
              <th className="py-2 pr-4">Status A</th>
              <th className="py-2 pr-4">Status B</th>
              <th className="py-2"></th>
            </tr>
          </thead>
          <tbody>
            {scenarios.map((s: ScenarioDiff) => (
              <React.Fragment key={s.scenario_id}>
                <tr
                  className={`border-b cursor-pointer hover:brightness-95 transition-colors ${rowBg(s.delta)}`}
                  onClick={() => toggle(s.scenario_id)}
                >
                  <td className="py-2 pr-4 font-mono font-medium">{s.scenario_id}</td>
                  <td className="py-2 pr-4 text-right">{scoreCell(s.score_a)}</td>
                  <td className="py-2 pr-4 text-right">{scoreCell(s.score_b)}</td>
                  <td className="py-2 pr-4 text-right">{deltaChip(s.delta)}</td>
                  <td className="py-2 pr-4">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        s.status_a === 'pass'
                          ? 'bg-green-100 text-green-800'
                          : s.status_a === 'missing'
                          ? 'bg-gray-100 text-gray-500'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {s.status_a}
                    </span>
                  </td>
                  <td className="py-2 pr-4">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        s.status_b === 'pass'
                          ? 'bg-green-100 text-green-800'
                          : s.status_b === 'missing'
                          ? 'bg-gray-100 text-gray-500'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {s.status_b}
                    </span>
                  </td>
                  <td className="py-2 text-gray-400 text-xs">
                    {expanded.has(s.scenario_id) ? '▲' : '▼'}
                  </td>
                </tr>
                {expanded.has(s.scenario_id) && s.criteria.length > 0 && (
                  <tr key={`${s.scenario_id}-crit-header`}>
                    <td colSpan={7} className="p-0">
                      <table className="w-full text-xs border-collapse">
                        <thead>
                          <tr className="bg-gray-50 border-b text-gray-500">
                            <th className="py-1 pl-8 pr-4 text-left font-normal">Criterion</th>
                            <th className="py-1 pr-4 text-right font-normal">Score A</th>
                            <th className="py-1 pr-4 text-right font-normal">Score B</th>
                            <th className="py-1 pr-4 text-right font-normal">Δ</th>
                            <th className="py-1 pr-4 text-center font-normal">Pass A</th>
                            <th className="py-1 text-center font-normal">Pass B</th>
                          </tr>
                        </thead>
                        <tbody>
                          <CriterionRows criteria={s.criteria} />
                        </tbody>
                      </table>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
