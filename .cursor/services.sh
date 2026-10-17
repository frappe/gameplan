#!/usr/bin/env bash

export PATH="/usr/bin:${HOME}/.local/bin:${PATH}"

MARIADB_ROOT_PASSWORD="${MARIADB_ROOT_PASSWORD:-123}"
SITE="${GAMEPLAN_SITE:-gameplan.localhost}"

start_mariadb() {
	if pgrep -x mariadbd >/dev/null 2>&1 || pgrep -x mysqld >/dev/null 2>&1; then
		return 0
	fi
	sudo service mariadb start
}

start_redis() {
	if pgrep -x redis-server >/dev/null 2>&1; then
		return 0
	fi
	sudo service redis-server start
}

wait_for_mariadb() {
	local attempt=0
	until mariadb -u root -p"${MARIADB_ROOT_PASSWORD}" -e "SELECT 1" &>/dev/null; do
		attempt=$((attempt + 1))
		if [ "${attempt}" -ge 60 ]; then
			echo "MariaDB did not become ready in time." >&2
			return 1
		fi
		sleep 1
	done
}

ensure_hosts_entry() {
	if ! grep -q "[[:space:]]${SITE}$" /etc/hosts; then
		echo "127.0.0.1 ${SITE}" | sudo tee -a /etc/hosts >/dev/null
	fi
}

ensure_repo_sites_link() {
	# frontend/src imports ../../../../sites/common_site_config.json. From the
	# repo checkout that resolves to /agent/sites, so link it to the bench sites dir.
	if [ -d "/agent" ]; then
		sudo ln -sfn "${HOME}/frappe-bench/sites" /agent/sites
	fi
}

ensure_services_ready() {
	start_mariadb
	start_redis
	wait_for_mariadb
	ensure_hosts_entry
	ensure_repo_sites_link
}
