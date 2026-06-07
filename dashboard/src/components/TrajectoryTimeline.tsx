'use client'

import { useState, useEffect } from 'react'
import { Span } from '@/lib/api'

function getDuration(span: Span): string {
  const ms =
    new Date(span.ended_at).getTime() - new Date(span.started_at).getTime()
  if (ms <= 0) return '<1ms'
  return `${ms}ms`
}

function borderColor(type: string): string {
  switch (type) {
    case 'model_call':
      return 'border-l-blue-500'
    case 'tool_call':
      return 'border-l-amber-500'
    case 'tool_result':
      return 'border-l-green-500'
    case 'final_output':
      return 'border-l-violet-500'
    default:
      return 'border-l-gray-400'
  }
}

function typeBadgeColor(type: string): string {
  switch (type) {
    case 'model_call':
      return 'bg-blue-100 text-blue-800'
    case 'tool_call':
      return 'bg-amber-100 text-amber-800'
    case 'tool_result':
      return 'bg-green-100 text-green-800'
    case 'final_output':
      return 'bg-violet-100 text-violet-800'
    default:
      return 'bg-gray-100 text-gray-700'
  }
}

function SpanHeader({ span }: { span: Span }) {
  const d = span.data as Record<string, unknown>

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span
        className={`px-1.5 py-0.5 rounded text-xs font-medium ${typeBadgeColor(span.type)}`}
      >
        {span.type}
      </span>
      {span.type === 'model_call' && (
        <>
          {d.model && (
            <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 text-xs font-mono">
              {String(d.model)}
            </span>
          )}
          {typeof d.input_tokens === 'number' && (
            <span className="text-xs text-gray-500">↑{d.input_tokens}</span>
          )}
          {typeof d.output_tokens === 'number' && (
            <span className="text-xs text-gray-500">↓{d.output_tokens}</span>
          )}
        </>
      )}
      {(span.type === 'tool_call' || span.type === 'tool_result') && d.tool_name && (
        <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-700 text-xs font-mono">
          {String(d.tool_name)}
        </span>
      )}
      <span className="ml-auto text-xs text-gray-400">{getDuration(span)}</span>
    </div>
  )
}

function SpanBody({ span }: { span: Span }) {
  const d = span.data as Record<string, unknown>

  if (span.type === 'model_call') {
    return (
      <div className="space-y-2 mt-2">
        {d.input_messages !== undefined && (
          <div>
            <p className="text-xs text-gray-500 mb-1">Input messages</p>
            <pre className="max-h-40 overflow-y-auto font-mono text-xs bg-gray-50 p-2 rounded border text-gray-700 whitespace-pre-wrap break-all">
              {JSON.stringify(d.input_messages, null, 2)}
            </pre>
          </div>
        )}
        {d.output_content !== undefined && (
          <div>
            <p className="text-xs text-gray-500 mb-1">Output</p>
            <pre className="max-h-40 overflow-y-auto font-mono text-xs bg-gray-50 p-2 rounded border text-gray-700 whitespace-pre-wrap break-all">
              {JSON.stringify(d.output_content, null, 2)}
            </pre>
          </div>
        )}
      </div>
    )
  }

  if (span.type === 'tool_call') {
    return (
      <div className="mt-2">
        <p className="text-xs text-gray-500 mb-1">Tool input</p>
        <pre className="max-h-40 overflow-y-auto font-mono text-xs bg-gray-50 p-2 rounded border text-gray-700 whitespace-pre-wrap break-all">
          {JSON.stringify(d.tool_input, null, 2)}
        </pre>
      </div>
    )
  }

  if (span.type === 'tool_result') {
    return (
      <div className="mt-2">
        <p className="text-xs text-gray-500 mb-1">Content</p>
        <pre className="max-h-40 overflow-y-auto font-mono text-xs bg-gray-50 p-2 rounded border text-gray-700 whitespace-pre-wrap break-all">
          {String(d.content ?? '')}
        </pre>
      </div>
    )
  }

  if (span.type === 'final_output') {
    return (
      <div className="mt-2">
        <p className="text-xs text-gray-500 mb-1">Output</p>
        <p className="text-sm text-gray-700 whitespace-pre-wrap">{String(d.text ?? '')}</p>
      </div>
    )
  }

  return null
}

interface Props {
  spans: Span[]
  finalOutput: string | null
  highlightedSpanId: string | null
}

export default function TrajectoryTimeline({ spans, finalOutput, highlightedSpanId }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!highlightedSpanId) return
    setExpanded((prev) => new Set([...prev, highlightedSpanId]))
    document
      .getElementById(`span-${highlightedSpanId}`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [highlightedSpanId])

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  if (spans.length === 0) {
    return (
      <p className="text-gray-500 text-sm">
        No trajectory spans recorded.
        {finalOutput && (
          <span className="block mt-2 text-gray-700">{finalOutput}</span>
        )}
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {spans.map((span) => {
        const isHighlighted = span.id === highlightedSpanId
        const isExpanded = expanded.has(span.id)

        return (
          <div
            key={span.id}
            id={`span-${span.id}`}
            className={`bg-white border-l-4 border rounded-lg p-3 shadow-sm transition-none ${borderColor(span.type)} ${
              isHighlighted ? 'ring-2 ring-blue-500' : ''
            }`}
          >
            <div className="flex items-start gap-2">
              <div className="flex-1 min-w-0">
                <SpanHeader span={span} />
                {isExpanded && <SpanBody span={span} />}
              </div>
              <button
                onClick={() => toggle(span.id)}
                className="shrink-0 text-gray-400 hover:text-gray-700 mt-0.5"
                aria-label={isExpanded ? 'Collapse' : 'Expand'}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                >
                  <path
                    fillRule="evenodd"
                    d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
