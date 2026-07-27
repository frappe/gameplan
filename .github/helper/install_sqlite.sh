#!/bin/bash
# Provision a Frappe bench with a SQLite-backed Gameplan site for CI.
# SQLite is a serverless backend, so no database server/credentials are needed.
set -e
cd ~ || exit

echo "Setting Up Bench..."

pip install frappe-bench
bench -v init frappe-bench --skip-assets --python "$(which python)"
cd ./frappe-bench || exit

bench -v setup requirements

echo "Setting Up Gameplan App..."
bench get-app gameplan "${GITHUB_WORKSPACE}"

echo "Setting Up Procfile..."
sed -i 's/^watch:/# watch:/g' Procfile
sed -i 's/^schedule:/# schedule:/g' Procfile

echo "Setting up redisearch module..."
echo "loadmodule ${GITHUB_WORKSPACE}/.github/helper/redisearch.so" >> ./config/redis_cache.conf
chmod +x "${GITHUB_WORKSPACE}/.github/helper/redisearch.so"
cat ./config/redis_cache.conf

echo "Starting Bench..."
bench start &> bench_start.log &

# Build frontend assets in parallel (matches the MariaDB install.sh): backend
# tests that render a page or resolve the asset manifest need them present.
CI=Yes bench build &> bench_build.log &
build_pid=$!

# Site creation / migrate talk to redis_cache & redis_queue, so wait for the
# bench processes (started above) to come up before provisioning the site.
sleep 20

# Each step is wrapped in `timeout` with stdin from /dev/null so a hung or
# unexpectedly-interactive command fails the job quickly (with its output in
# the log) instead of stalling until the 60-minute job timeout.
echo "Creating SQLite Site..."
timeout 600 bench new-site gameplan.test \
	--db-type sqlite \
	--admin-password admin \
	--force </dev/null

# Test/runtime flags that the MariaDB site gets from .github/helper/site_config.json.
# Stored with --parse so they are native JSON types (booleans), not strings.
# --parse runs ast.literal_eval, so values must be Python literals (True/1), not true.
bench --site gameplan.test set-config --parse allow_tests True
bench --site gameplan.test set-config --parse enable_ui_tests True
bench --site gameplan.test set-config --parse server_script_enabled True
bench --site gameplan.test set-config --parse mute_emails True
bench --site gameplan.test set-config --parse ignore_csrf 1

echo "Installing Gameplan app..."
timeout 600 bench --site gameplan.test install-app gameplan </dev/null

echo "Building search index..."
timeout 300 bench --site gameplan.test execute gameplan.search_sqlite.rebuild_index </dev/null

# Wait for the asset build started above to finish before tests run.
wait $build_pid
