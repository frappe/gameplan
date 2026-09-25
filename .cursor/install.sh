#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAMEPLAN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BENCH_DIR="${HOME}/frappe-bench"
MARIADB_ROOT_PASSWORD="${MARIADB_ROOT_PASSWORD:-123}"
SITE="${GAMEPLAN_SITE:-gameplan.localhost}"
FRAPPE_BRANCH="${FRAPPE_BRANCH:-version-16}"

source "${SCRIPT_DIR}/services.sh"
ensure_services_ready

echo "Gameplan root: ${GAMEPLAN_ROOT}"

cd "${GAMEPLAN_ROOT}"
git submodule update --init --recursive

cd "${GAMEPLAN_ROOT}/frontend"
yarn install --frozen-lockfile

if [ -d "${BENCH_DIR}/apps/frappe" ]; then
	echo "Bench already initialised, skipping setup."
	exit 0
fi

echo "Initialising frappe-bench..."
bench init --skip-redis-config-generation --frappe-branch "${FRAPPE_BRANCH}" \
	--python "$(command -v python3.14)" \
	"${BENCH_DIR}"
cd "${BENCH_DIR}"

bench set-mariadb-host 127.0.0.1
bench set-redis-cache-host 127.0.0.1:6379
bench set-redis-queue-host 127.0.0.1:6379
bench set-redis-socketio-host 127.0.0.1:6379

sed -i '/redis/d' ./Procfile
sed -i '/watch/d' ./Procfile

echo "Installing gameplan app from checkout..."
bench get-app gameplan "${GAMEPLAN_ROOT}"
rm -rf apps/gameplan
ln -sfn "${GAMEPLAN_ROOT}" apps/gameplan
./env/bin/pip install -e apps/gameplan

echo "Creating development site..."
bench new-site "${SITE}" \
	--force \
	--mariadb-root-password "${MARIADB_ROOT_PASSWORD}" \
	--admin-password admin \
	--no-mariadb-socket

bench --site "${SITE}" install-app gameplan
bench --site "${SITE}" set-config developer_mode 1
bench --site "${SITE}" set-config mute_emails 1
bench --site "${SITE}" set-config allow_tests 1
bench --site "${SITE}" set-config enable_ui_tests 1
bench --site "${SITE}" add-user alex@example.com \
	--first-name Alex \
	--last-name Scott \
	--password 123 \
	--user-type "System User" \
	--add-role "Gameplan Admin"
bench use "${SITE}"

echo "Gameplan install complete."
