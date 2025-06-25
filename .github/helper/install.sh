#!/bin/bash
set -e
cd ~ || exit

echo "Setting Up Bench..."

pip install frappe-bench
bench -v init frappe-bench --skip-assets --python "$(which python)"
cd ./frappe-bench || exit

bench -v setup requirements

echo "Setting Up Gameplan App..."
bench get-app gameplan "${GITHUB_WORKSPACE}"

echo "Setting Up Sites & Database..."

mkdir ~/frappe-bench/sites/gameplan.test
cp "${GITHUB_WORKSPACE}/.github/helper/site_config.json" ~/frappe-bench/sites/gameplan.test/site_config.json

mariadb --host 127.0.0.1 --port 3306 -u root -p123 -e "SET GLOBAL character_set_server = 'utf8mb4'";
mariadb --host 127.0.0.1 --port 3306 -u root -p123 -e "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'";

mariadb --host 127.0.0.1 --port 3306 -u root -p123 -e "CREATE DATABASE test_gameplan";
mariadb --host 127.0.0.1 --port 3306 -u root -p123 -e "CREATE USER 'test_gameplan'@'localhost' IDENTIFIED BY 'test_gameplan'";
mariadb --host 127.0.0.1 --port 3306 -u root -p123 -e "GRANT ALL PRIVILEGES ON \`test_gameplan\`.* TO 'test_gameplan'@'localhost'";

mariadb --host 127.0.0.1 --port 3306 -u root -p123 -e "FLUSH PRIVILEGES";


echo "Setting Up Procfile..."

sed -i 's/^watch:/# watch:/g' Procfile
sed -i 's/^schedule:/# schedule:/g' Procfile

echo "Setting up redisearch module..."
echo "loadmodule ${GITHUB_WORKSPACE}/.github/helper/redisearch.so" >> ./config/redis_cache.conf
chmod +x "${GITHUB_WORKSPACE}/.github/helper/redisearch.so"
cat ./config/redis_cache.conf

echo "Starting Bench..."

bench start &> bench_start.log &

CI=Yes bench build &
build_pid=$!

bench --site gameplan.test reinstall --yes
bench --site gameplan.test install-app gameplan
bench --site gameplan.test execute gameplan.search_sqlite.build_index_if_not_exists

# wait till assets are built succesfully
wait $build_pid
