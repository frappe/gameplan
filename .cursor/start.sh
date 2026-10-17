#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/services.sh"

ensure_services_ready

SITE="${GAMEPLAN_SITE:-gameplan.localhost}"
if curl -sf "http://${SITE}:8000/api/method/ping" >/dev/null 2>&1; then
	echo "Frappe backend is already responding."
else
	echo "Infrastructure ready. Start bench and vite from terminals."
fi
