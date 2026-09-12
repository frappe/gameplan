// Central, env-overridable configuration for the offline Playwright suite. Defaults match
// the seeded `gameplan.localhost` dev site this suite was developed against (see
// README.md for how to reproduce that seed). Every story/helper reads its URLs, creds,
// and seeded-content IDs from here instead of hardcoding them, so the suite can run
// against a differently-seeded site by only setting env vars.
const path = require('path')

const BASE = process.env.GAMEPLAN_OFFLINE_BASE_URL || 'http://gameplan.localhost:8003'
const EMAIL = process.env.GAMEPLAN_OFFLINE_USER || 'offline-tester@example.com'
const PWD = process.env.GAMEPLAN_OFFLINE_PASSWORD || 'offline-test-1234'
// Second account, used by US7b to simulate a second person logging in on the same shared
// computer right after the first — needs to be a distinct identity, member of the same
// community so it can see the same seeded Space.
const EMAIL2 = process.env.GAMEPLAN_OFFLINE_USER2 || 'offline-tester-2@example.com'
const PWD2 = process.env.GAMEPLAN_OFFLINE_PASSWORD2 || 'offline-test-1234'
const FULL_NAME = process.env.GAMEPLAN_OFFLINE_FULL_NAME || 'Offline Tester'
const FULL_NAME2 = process.env.GAMEPLAN_OFFLINE_FULL_NAME2 || 'Offline Tester Two'

// Seeded content coordinates (GP Team/GP Project/GP Discussion names) — see README.md.
const COMMUNITY = process.env.GAMEPLAN_OFFLINE_COMMUNITY || 'common-room'
const SPACE_ID = process.env.GAMEPLAN_OFFLINE_SPACE_ID || '3'
const DISCUSSION_ID = process.env.GAMEPLAN_OFFLINE_DISCUSSION_ID || '55'
// Never visited by any story before going offline -> used for US6 "uncached content".
const UNCACHED_SPACE_ID = process.env.GAMEPLAN_OFFLINE_UNCACHED_SPACE_ID || '4'
const UNCACHED_DISCUSSION_SPACE_ID =
  process.env.GAMEPLAN_OFFLINE_UNCACHED_DISCUSSION_SPACE_ID || '5'
const UNCACHED_DISCUSSION_ID = process.env.GAMEPLAN_OFFLINE_UNCACHED_DISCUSSION_ID || '54'

const URLS = {
  feed: `${BASE}/g`,
  spaceDiscussions: `${BASE}/g/community/${COMMUNITY}/space/${SPACE_ID}/discussions`,
  discussion: `${BASE}/g/community/${COMMUNITY}/space/${SPACE_ID}/discussion/${DISCUSSION_ID}`,
  uncachedDiscussion: `${BASE}/g/community/${COMMUNITY}/space/${UNCACHED_DISCUSSION_SPACE_ID}/discussion/${UNCACHED_DISCUSSION_ID}`,
  uncachedSpace: `${BASE}/g/community/${COMMUNITY}/space/${UNCACHED_SPACE_ID}/discussions`,
  people: `${BASE}/g/people`,
  person: (id) => `${BASE}/g/people/${id}`,
  personPosts: (id) => `${BASE}/g/people/${id}/posts`,
}

// Real, enabled `GP User Profile` members on the seeded site, used across the
// People/profile (P1-P3) stories. Kept distinct per role so no story's "never visited"
// member is accidentally warmed by another story's "visited" step within the same run.
const PEOPLE = {
  // P1: never opened in that story's context; relies entirely on the background
  // prefetcher (data/offlinePrefetch.ts) to be offline-ready.
  neverVisitedForPrefetch: process.env.GAMEPLAN_OFFLINE_PERSON_PREFETCH || 'priya-sharma',
  // P2: visited fully online (profile + Posts tab) before going offline.
  visitedFully: process.env.GAMEPLAN_OFFLINE_PERSON_VISITED || 'maya-iyer',
  // P3: opened only after immediately forcing offline, before prefetch can run.
  neverVisitedNoPrefetch: process.env.GAMEPLAN_OFFLINE_PERSON_NO_PREFETCH || 'hana-suzuki',
}

// frontend/tests/offline -> the gameplan app root (used by us8.js to rebuild after
// bumping gameplan-sw.js's CACHE_VERSION).
const APP_DIR = path.join(__dirname, '..', '..', '..')
const RESULTS_DIR = process.env.GAMEPLAN_OFFLINE_RESULTS_DIR || path.join(__dirname, 'results')
const SHOTS_DIR = path.join(RESULTS_DIR, 'screenshots')

module.exports = {
  BASE,
  EMAIL,
  PWD,
  EMAIL2,
  PWD2,
  FULL_NAME,
  FULL_NAME2,
  URLS,
  PEOPLE,
  APP_DIR,
  RESULTS_DIR,
  SHOTS_DIR,
}
