#!/usr/bin/env bash
# record_demo.sh — run the example suite and open the dashboard
set -euo pipefail

cd "$(dirname "$0")/backend"

echo "=== Running research_agent_suite ==="
uv run rubricon run examples/research_agent_suite.yaml

echo ""
echo "=== Starting API server in background ==="
uv run rubricon serve &
API_PID=$!

# Give uvicorn 2 seconds to bind
sleep 2

echo ""
echo "Dashboard: http://localhost:3000  (start 'pnpm dev' in dashboard/ if not running)"
echo "API:       http://localhost:8000"
echo ""
echo "Press Enter to stop the API server..."
read -r

kill "$API_PID" 2>/dev/null || true
echo "Done."
