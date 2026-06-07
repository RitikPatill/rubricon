import { getComparison } from '@/lib/api'
import CompareView from '@/components/CompareView'

export const dynamic = 'force-dynamic'

export default async function ComparePage({
  searchParams,
}: {
  searchParams: { run_a?: string | string[]; run_b?: string | string[] }
}) {
  const runA = typeof searchParams.run_a === 'string' ? searchParams.run_a : undefined
  const runB = typeof searchParams.run_b === 'string' ? searchParams.run_b : undefined

  if (!runA || !runB) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-4">Compare Runs</h1>
        <p className="text-gray-500">
          Select two runs from the{' '}
          <a href="/runs" className="text-blue-600 hover:underline">
            runs list
          </a>{' '}
          to compare them.
        </p>
      </div>
    )
  }

  let data
  try {
    data = await getComparison(runA, runB)
  } catch {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-4">Compare Runs</h1>
        <p className="text-red-600">Could not load comparison. One or both run IDs may be invalid.</p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Compare Runs</h1>
      <CompareView data={data} />
    </div>
  )
}
