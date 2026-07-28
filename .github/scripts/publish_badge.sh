#!/usr/bin/env bash
#
# Publish a generated badge SVG to its own orphan branch.
#
#   publish_badge.sh <svg-path> <branch>
#
# The badge is deliberately not committed to develop: a commit per coverage change
# is noise in the history people actually read. It lives on a branch nobody merges,
# force-pushed to a single commit so that branch never accumulates either, and the
# README links it by raw URL.
#
# Each badge gets its OWN branch. server-tests.yml and ui-test.yml both fire on a
# push to develop, so a shared branch would have them force-pushing over each other
# and dropping whichever badge lost the race.
#
# Requires GH_TOKEN. Callers run this with continue-on-error: a badge that cannot be
# published must never redden a green suite.
set -euo pipefail

badge="${1:?usage: publish_badge.sh <svg-path> <branch>}"
branch="${2:?usage: publish_badge.sh <svg-path> <branch>}"

if [ ! -s "$badge" ]; then
	echo "No badge at ${badge}; nothing to publish."
	exit 0
fi

if git fetch --depth=1 origin "$branch" 2>/dev/null &&
	git show FETCH_HEAD:coverage.svg 2>/dev/null | diff -q - "$badge" >/dev/null; then
	echo "Badge on ${branch} is unchanged."
	exit 0
fi

# Built as a throwaway single-commit repo rather than an orphan branch in this
# checkout, so the working tree and index of the branch under test are never touched.
work="$(mktemp -d)"
cp "$badge" "${work}/coverage.svg"
cd "$work"
git init -q
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add coverage.svg
git commit -q -m "chore: coverage badge for ${GITHUB_SHA:-unknown}"
git push --force \
	"https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" "HEAD:${branch}"

echo "Published $(basename "$badge") to ${branch}."
