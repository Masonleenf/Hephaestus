#!/usr/bin/env bash
# Verify routing cards (Hephaestus Network 2.0).
#
# Usage:
#   scripts/verify-routing-cards.sh [folder]   # lint every .agentlas/routing-card.json under folder (default: .)
#   scripts/verify-routing-cards.sh --global   # lint the global ~/.agentlas/networking cards
#
# Exit codes: 0 = no schema errors (quality-gate blockers are reported but do
# not fail the script — cards below routing_ready are simply excluded from
# auto routing); 1 = at least one malformed card.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

target="${1:-.}"
if [[ "$target" == "--global" ]]; then
  PYTHONPATH="$root${PYTHONPATH:+:$PYTHONPATH}" python3 -m agentlas_cloud cards lint
else
  PYTHONPATH="$root${PYTHONPATH:+:$PYTHONPATH}" python3 -m agentlas_cloud cards lint "$target"
fi
