import { getRuns } from '@/lib/api'
import RunsListClient from '@/components/RunsListClient'

export const dynamic = 'force-dynamic'

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
      <RunsListClient runs={runs} />
    </div>
  )
}
