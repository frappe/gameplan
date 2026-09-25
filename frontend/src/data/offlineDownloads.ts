import { reactive, watch } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import { call, toast } from 'frappe-ui'
import { delMany, get, getMany, set, setMany, values } from 'idb-keyval'
import { cachedDocNames, cachedListKeys, docKey, listKey } from './offline/cache'
import { OFFLINE_ACTION_MESSAGE, isNetworkError } from './offline/requests'
import { isOnline, onReconnect, saveData } from './online'
import { session } from './session'
import { getSessionUserFromCookie } from '@/utils/sessionCookie'
import { customEmojis } from './customEmojis'
import { communityFeedKey, feedScope, spaceFeedKey } from './discussions'
import {
  ACTIVITY_FIELDS,
  COMMENT_FIELDS,
  POLL_FIELDS,
  activitiesCacheKey,
  commentsCacheKey,
  pollsCacheKey,
} from './discussionTimeline'

/**
 * "Download for offline": keeps the chosen window of discussions on the device, filed into the
 * same entries frappe-ui's resources read (offline/cache.ts), so a downloaded discussion opens
 * like a visited one.
 */

export type OfflineWindow = 0 | 7 | 30 | 90

export const WINDOW_OPTIONS: { label: string; value: OfflineWindow }[] = [
  { label: 'Recently viewed only', value: 0 },
  { label: 'Past week', value: 7 },
  { label: 'Past month', value: 30 },
  { label: 'Past 3 months', value: 90 },
]

const INDEX = 'gameplan.offline_downloads.get_offline_index'
const BUNDLE = 'gameplan.offline_downloads.get_offline_bundle'
const META_KEY = 'gameplan:offline-downloads'
const LOCK_NAME = 'gameplan-offline-downloads'
// PAGE_SIZE, MAX_DISCUSSIONS and VISIT_CHECK_LIMIT mirror gameplan/offline_downloads.py.
const PAGE_SIZE = 20
export const MAX_DISCUSSIONS = 500
const VISIT_CHECK_LIMIT = 2000
const MAX_IMAGES = 300
// Each background sync still costs an index query, so they are kept to a few a day.
const SYNC_INTERVAL = 6 * 60 * 60 * 1000
// A failed sync backs off from here, doubling up to SYNC_INTERVAL.
const RETRY_DELAY = 5 * 60 * 1000
// Spreads the first sync so a team opening the app together doesn't sync together.
const MAX_START_DELAY = 30 * 1000
// gameplan-sw.js's cache for the images of downloaded discussions.
const IMAGE_CACHE_SUFFIX = ':downloads'
// useDiscussions' page size, so a restored feed holds as much as a fetched one.
const FEED_LIMIT = 50

interface Meta {
  user: string
  window: number
  /** Server time the last complete sync started. */
  since: string | null
  /** Downloaded discussions, each with where the index said it sat. */
  places: Record<string, string>
  /** Where the rotating check of visited discussions resumes. */
  checkedUpTo?: string
  lastSyncedAt: number | null
  incomplete: boolean
  failures?: number
  /** No automatic run before this; a manual one goes ahead. */
  retryAfter?: number
}

interface Index {
  discussions: string[]
  places: Record<string, string>
  changed: string[]
  revoked: string[]
  synced_at: string
}

interface Bundle {
  discussions: Array<Record<string, unknown> & { name: string | number }>
  /** The same discussions as the feeds list them. */
  rows: FeedRow[]
  comments: Record<string, Row[]>
  activities: Record<string, Row[]>
  polls: Record<string, Row[]>
}

type Row = Record<string, unknown> & { name: string | number }

type FeedRow = Row & {
  project?: string | number
  team?: string
  last_post_at?: string
  pinned_at?: string | null
  pin_scope?: string
}

interface Feed {
  key: string
  space?: string
  community?: string
  pinned: boolean
  /** Unread and Participating are the server's answer, so a sync only removes rows from them. */
  filtered?: boolean
}

export const offlineWindow = useLocalStorage<OfflineWindow>(
  `gameplan:offline-window:${session.user}`,
  0,
)

export const downloads = reactive({
  syncing: false,
  done: 0,
  total: 0,
  count: 0,
  lastSyncedAt: null as number | null,
  imagesSavedAt: null as number | null,
  error: null as string | null,
})

// This tab's running sync, so a removal can stop it.
let running: AbortController | null = null

/** Read inside the lock every time: another tab may have moved it on. */
async function readMeta(): Promise<Meta | null> {
  const stored = (await get(META_KEY).catch(() => null)) as Meta | undefined
  const meta = stored?.user === session.user && stored.places ? stored : null
  showMeta(meta)
  return meta
}

async function writeMeta(meta: Meta) {
  showMeta(meta)
  await set(META_KEY, meta)
}

function showMeta(meta: Meta | null) {
  downloads.count = meta ? Object.keys(meta.places).length : 0
  downloads.lastSyncedAt = meta?.lastSyncedAt ?? null
}

/**
 * Runs `task` holding the lock every tab shares, so one sync or removal runs at a time. With
 * `ifAvailable` it gives up rather than wait for another tab.
 */
function exclusive<T>(ifAvailable: boolean, task: () => Promise<T>): Promise<T | false> {
  if (!navigator.locks) return task()
  return navigator.locks.request(LOCK_NAME, { ifAvailable }, async (lock) =>
    lock ? task() : false,
  ) as Promise<T | false>
}

/**
 * Brings the device in line with the chosen window. A manual run waits for another tab's
 * run and then checks again; an automatic one leaves it to that tab and to the interval.
 */
function syncOfflineDownloads({ manual = false } = {}): Promise<boolean> {
  if (!session.isLoggedIn) return Promise.resolve(false)
  return exclusive(!manual, () => sync(manual))
}

async function sync(manual: boolean): Promise<boolean> {
  const days = offlineWindow.value
  const meta = await readMeta()
  if (!days) {
    if (meta) await forgetDownloads(meta)
    return true
  }
  if (!isOnline.value) return false
  if (!manual && !isDue(meta, days)) return true

  running = new AbortController()
  try {
    return await download(days, meta, running.signal)
  } finally {
    running = null
  }
}

function isDue(meta: Meta | null, days: OfflineWindow) {
  if (document.visibilityState !== 'visible' || saveData.value) return false
  if (meta?.retryAfter && Date.now() < meta.retryAfter) return false
  const fresh = meta?.window === days && !meta.incomplete && meta.lastSyncedAt
  return !fresh || Date.now() - fresh >= SYNC_INTERVAL
}

/** Whether the download finished; an interrupted one is resumed by the next run. */
async function download(days: OfflineWindow, previous: Meta | null, signal: AbortSignal) {
  const user = session.user!
  // The cache keys follow the cookie, which another tab's sign-in can change mid-sync.
  const switchedAccount = () => getSessionUserFromCookie() !== user
  const cancelled = () =>
    signal.aborted || offlineWindow.value !== days || switchedAccount() || !isOnline.value
  downloads.syncing = true
  downloads.error = null
  downloads.done = 0
  downloads.total = 0
  try {
    const onDevice = new Set(await cachedDocNames('GP Discussion'))
    // Only what is really on the device counts as downloaded. A new window keeps it.
    const places: Record<string, string> = {}
    for (const [name, place] of Object.entries(previous?.places ?? {})) {
      if (onDevice.has(name)) places[name] = place
    }
    const visits = visitsToCheck(
      [...onDevice].filter((name) => !(name in places)),
      previous?.checkedUpTo,
    )
    const index = await call<Index>(INDEX, {
      window_days: days,
      cached: visits.names,
      since: previous?.since ?? null,
    })
    if (cancelled()) return false

    await forgetDiscussions(index.revoked)
    // Out of the window now: no longer kept up to date, but left like any visited discussion.
    const inIndex = new Set(index.discussions)
    for (const name of Object.keys(places)) {
      if (!inIndex.has(name)) delete places[name]
    }
    const base: Meta = {
      user,
      window: days,
      since: previous?.since ?? null,
      places,
      checkedUpTo: visits.checkedUpTo,
      lastSyncedAt: previous?.lastSyncedAt ?? null,
      incomplete: true,
    }
    await writeMeta(base)

    // Changed, missing from the device, or moved to another Space or community.
    const changed = new Set(index.changed)
    const wanted = index.discussions.filter(
      (name) => changed.has(name) || places[name] !== index.places[name],
    )
    downloads.total = wanted.length
    const images = new Set<string>()
    const feedRows = new Map<string, FeedRow>()
    for (let i = 0; i < wanted.length; i += PAGE_SIZE) {
      if (i) await idle(signal)
      if (cancelled()) return false
      const bundle = await call<Bundle>(BUNDLE, {
        window_days: days,
        fields: { comments: COMMENT_FIELDS, activities: ACTIVITY_FIELDS, polls: POLL_FIELDS },
        names: wanted.slice(i, i + PAGE_SIZE),
      })
      // Never file one account's response under another's keys.
      if (switchedAccount()) return false
      // Recorded before the other checks, so a removal waiting on this run finds it.
      await storeBundle(bundle)
      for (const discussion of bundle.discussions) {
        const name = String(discussion.name)
        places[name] = index.places[name]
      }
      await writeMeta(base)
      if (cancelled()) return false
      for (const row of bundle.rows ?? []) feedRows.set(String(row.name), row)
      for (const url of bundleImages(bundle)) images.add(url)
      downloads.done = Math.min(i + PAGE_SIZE, wanted.length)
    }

    if (cancelled()) return false
    await storeFeeds(feedRows, new Set(index.revoked))
    const emojis = (customEmojis.data ?? []).map((emoji) => emoji.image).filter(Boolean)
    saveImages([...emojis, ...images].slice(0, MAX_IMAGES) as string[])
    await writeMeta({
      ...base,
      since: index.synced_at,
      lastSyncedAt: Date.now(),
      incomplete: false,
    })
    return true
  } catch (error) {
    downloads.error = error instanceof Error ? error.message : String(error)
    if (!cancelled()) await standDown(days, error).catch(() => {})
    throw error
  } finally {
    downloads.syncing = false
  }
}

/**
 * Backs automatic runs off after a failure; an unfinished sync is otherwise exempt from the
 * interval and would query the index on every tab focus. A lost connection is not counted,
 * so reconnecting still syncs at once.
 */
async function standDown(days: OfflineWindow, error: unknown) {
  if (isNetworkError(error)) return
  const meta = (await readMeta()) ?? {
    user: session.user!,
    window: days,
    since: null,
    places: {},
    lastSyncedAt: null,
    incomplete: true,
  }
  const failures = (meta.failures ?? 0) + 1
  const delay = Math.min(RETRY_DELAY * 2 ** (failures - 1), SYNC_INTERVAL)
  await writeMeta({ ...meta, incomplete: true, failures, retryAfter: Date.now() + delay })
}

/**
 * The visited discussions this sync checks for lost access. Past the per-request limit they are
 * walked in name order across syncs, so every one is eventually checked.
 */
function visitsToCheck(names: string[], after = '') {
  if (names.length <= VISIT_CHECK_LIMIT) return { names, checkedUpTo: '' }
  const sorted = [...names].sort()
  const found = sorted.findIndex((name) => name > after)
  const start = found === -1 ? 0 : found
  const slice = sorted.slice(start, start + VISIT_CHECK_LIMIT)
  return { names: slice, checkedUpTo: slice[slice.length - 1] }
}

/** The four entries a discussion occupies: its document and its three timeline lists. */
function discussionKeys(name: string) {
  return {
    doc: docKey('GP Discussion', name),
    comments: listKey(commentsCacheKey('GP Discussion', name)),
    activities: listKey(activitiesCacheKey('GP Discussion', name)),
    polls: listKey(pollsCacheKey(name)),
  }
}

async function storeBundle(bundle: Bundle) {
  const entries: [string, string][] = []
  for (const discussion of bundle.discussions) {
    const name = String(discussion.name)
    const key = discussionKeys(name)
    entries.push(
      [key.doc, JSON.stringify({ ...discussion, name })],
      [key.comments, rowsJson(bundle.comments[name])],
      [key.activities, rowsJson(bundle.activities[name])],
      [key.polls, rowsJson(bundle.polls[name])],
    )
  }
  await setMany(entries)
}

/**
 * Files downloaded rows into the Space and community feeds, merging with what they already
 * hold (a changes-only sync brings back only what changed) and dropping removed discussions.
 */
async function storeFeeds(rows: Map<string, FeedRow>, removed: Set<string>) {
  if (!rows.size && !removed.size) return
  const bySpace = new Map<string, FeedRow[]>()
  const byCommunity = new Map<string, FeedRow[]>()
  const group = (index: Map<string, FeedRow[]>, id: string, row: FeedRow) => {
    const list = index.get(id)
    if (list) list.push(row)
    else index.set(id, [row])
  }
  for (const row of rows.values()) {
    if (row.project != null) group(bySpace, String(row.project), row)
    if (row.team) group(byCommunity, row.team, row)
  }

  const feeds = new Map<string, Feed>()
  for (const feed of [...downloadedFeeds(rows.values()), ...(await cachedFeeds())]) {
    feeds.set(feed.key, feed)
  }
  if (!feeds.size) return

  const targets = [...feeds.values()]
  const stored = await getMany(targets.map((feed) => feed.key)).catch(() => [])
  const entries: [string, string][] = []
  targets.forEach((feed, index) => {
    const candidates = feed.filtered
      ? []
      : ((feed.space ? bySpace.get(feed.space) : byCommunity.get(feed.community!)) ?? [])
    const merged = new Map<string, FeedRow>()
    for (const row of parseRows(stored[index])) {
      const name = String(row.name)
      const fresh = rows.get(name)
      // A discussion that moved leaves the feed it came from.
      if (removed.has(name) || (fresh && !belongsTo(fresh, feed))) continue
      merged.set(name, fresh ?? row)
    }
    for (const row of candidates) {
      if (belongsTo(row, feed)) merged.set(String(row.name), row)
    }

    // Never shrink a feed someone paged through online.
    const limit = feed.pinned ? Infinity : Math.max(FEED_LIMIT, parseRows(stored[index]).length)
    const order = feed.pinned ? 'pinned_at' : 'last_post_at'
    const next = [...merged.values()]
      .sort((a, b) => String(b[order] ?? '').localeCompare(String(a[order] ?? '')))
      .slice(0, limit)
      .map((row) => ({ ...row, name: String(row.name) }))

    const value = JSON.stringify(next)
    if (value !== stored[index]) entries.push([feed.key, value])
  })
  if (entries.length) await setMany(entries)
}

/** The feeds a downloaded row belongs to, opened on this device or not. */
function downloadedFeeds(rows: Iterable<FeedRow>): Feed[] {
  const feeds = new Map<string, Feed>()
  for (const row of rows) {
    const scopes = [
      row.project != null && { space: String(row.project), name: spaceFeedKey(row.project) },
      row.team && { community: row.team, name: communityFeedKey(row.team) },
    ]
    for (const scope of scopes) {
      if (!scope) continue
      const { name, ...where } = scope
      for (const pinned of row.pinned_at ? [false, true] : [false]) {
        const key = listKey(['Discussions', pinned ? ['pinned', name] : name])
        feeds.set(key, { ...where, key, pinned })
      }
    }
  }
  return [...feeds.values()]
}

/** Feeds this user has cached, so rows that moved or went away leave them too. */
async function cachedFeeds(): Promise<Feed[]> {
  const feeds: Feed[] = []
  for (const cacheKey of await cachedListKeys('Discussions')) {
    const inner = cacheKey[1]
    const pinned = Array.isArray(inner) && inner[0] === 'pinned'
    const name = pinned ? inner[1] : inner
    const scope = typeof name === 'string' ? feedScope(name) : null
    if (!scope) continue
    const { space, community, feedType } = scope
    feeds.push({
      key: listKey(cacheKey),
      space,
      community,
      pinned,
      filtered: Boolean(feedType && feedType !== 'recent'),
    })
  }
  return feeds
}

function belongsTo(row: FeedRow, feed: Feed) {
  const inScope = feed.space ? String(row.project) === feed.space : row.team === feed.community
  if (!inScope || !feed.pinned) return inScope
  // A community pin shows in its Space too; a Space pin only there (DiscussionList.vue).
  if (!row.pinned_at) return false
  return feed.space
    ? row.pin_scope === 'Space' || row.pin_scope === 'Category'
    : row.pin_scope === 'Category'
}

function parseRows(value: unknown): FeedRow[] {
  if (typeof value !== 'string') return []
  try {
    const rows = JSON.parse(value)
    return Array.isArray(rows) ? rows : []
  } catch {
    return []
  }
}

async function forgetDiscussions(names: string[]) {
  if (!names.length) return
  const keys = names.map((name) => discussionKeys(name))
  // Only the document and comments can hold images.
  const stored = await getMany(keys.flatMap((key) => [key.doc, key.comments])).catch(() => [])
  await delMany(keys.flatMap(Object.values))

  // Their images go too, unless something still on the device shows them.
  const images = new Set(stored.flatMap((value) => (value ? htmlImages(value) : [])))
  if (!images.size) return
  const inUse = await imagesInUse().catch(() => null)
  if (!inUse) return
  forgetImages([...images].filter((url) => !inUse.has(url)))
}

async function imagesInUse() {
  const inUse = new Set<string>((customEmojis.data ?? []).map((emoji) => emoji.image))
  for (const value of await values()) {
    for (const url of htmlImages(value)) inUse.add(url)
  }
  return inUse
}

function bundleImages(bundle: Bundle) {
  return [
    ...bundle.discussions.flatMap((discussion) => htmlImages(discussion.content)),
    ...Object.values(bundle.comments)
      .flat()
      .flatMap((comment) => htmlImages(comment.content)),
  ]
}

/** Uploaded images an HTML string (or a stored JSON copy of rows holding HTML) shows. */
function htmlImages(html: unknown) {
  if (typeof html !== 'string') return []
  return [...html.matchAll(/<img[^>]+src=\\?["']([^"'\\]+)/g)].map(([, src]) => src)
}

function saveImages(urls: string[]) {
  if (urls.length) navigator.serviceWorker?.controller?.postMessage({ type: 'CACHE_IMAGES', urls })
}

function forgetImages(urls: string[]) {
  if (urls.length) navigator.serviceWorker?.controller?.postMessage({ type: 'FORGET_IMAGES', urls })
}

/** What the downloads weigh: their own entries and the images saved for them. */
export async function downloadedBytes(): Promise<number> {
  const meta = await readMeta()
  if (!meta) return 0
  const owned = Object.keys(meta.places).flatMap((name) => Object.values(discussionKeys(name)))
  const encoder = new TextEncoder()
  const images = new Set<string>()
  let bytes = 0
  for (const value of await getMany(owned)) {
    if (typeof value !== 'string') continue
    bytes += encoder.encode(value).length
    for (const url of htmlImages(value)) images.add(url)
  }
  return bytes + (await savedImageBytes([...images]))
}

/** From the headers; reading the bodies back would cost more than the figure is worth. */
async function savedImageBytes(urls: string[]): Promise<number> {
  if (!urls.length || typeof caches === 'undefined') return 0
  const name = (await caches.keys()).find((key) => key.endsWith(IMAGE_CACHE_SUFFIX))
  if (!name) return 0
  const cache = await caches.open(name)
  const responses = await Promise.all(urls.map((url) => cache.match(url).catch(() => null)))
  return responses.reduce(
    (bytes, response) => bytes + (Number(response?.headers.get('content-length')) || 0),
    0,
  )
}

/** Deletes everything downloaded, once this tab's sync has stopped. */
function removeOfflineDownloads() {
  running?.abort()
  return exclusive(false, async () => {
    const meta = await readMeta()
    if (meta) await forgetDownloads(meta)
  })
}

async function forgetDownloads(meta: Meta) {
  await forgetDiscussions(Object.keys(meta.places))
  await delMany([META_KEY])
  showMeta(null)
}

/** Picks a window and downloads it now. */
export function downloadForOffline(days: OfflineWindow) {
  // A dialog opened before the connection dropped can still confirm.
  if (days && !isOnline.value) {
    toast.warning(OFFLINE_ACTION_MESSAGE, { id: 'offline-action' })
    return
  }
  offlineWindow.value = days
  if (!days) return removeOfflineDownloads()
  // Otherwise the browser may evict the downloads (Safari does after a week unused).
  navigator.storage?.persist?.().catch(() => {})
  const finished = syncOfflineDownloads({ manual: true }).then((done) => {
    if (!done) throw new Error('Offline download did not finish')
  })
  return toast.promise(finished, {
    id: 'offline-download',
    loading: 'Downloading discussions for offline reading…',
    success: 'Discussions are ready to read offline',
    error: 'Could not finish the offline download. It will retry later.',
  })
}

/** Rows as the server sends them, with string names. Each list runs its transform on them. */
function rowsJson(rows: Row[] = []) {
  return JSON.stringify(rows.map((row) => ({ ...row, name: String(row.name) })))
}

/** Yields to the page between bundle pages, or at once when the sync is cancelled. */
function idle(signal: AbortSignal) {
  return new Promise<void>((resolve) => {
    if (signal.aborted) return resolve()
    signal.addEventListener('abort', () => resolve(), { once: true })
    if ('requestIdleCallback' in window) requestIdleCallback(() => resolve(), { timeout: 2000 })
    else setTimeout(resolve, 200)
  })
}

/** Syncs shortly after load, then on reconnect and when the tab returns. */
export function setupOfflineDownloads() {
  const background = () => syncOfflineDownloads().catch(() => {})
  navigator.serviceWorker?.addEventListener('message', (event) => {
    if (event.data?.type === 'IMAGES_SAVED') downloads.imagesSavedAt = Date.now()
  })
  readMeta()
  setTimeout(background, 5000 + Math.random() * MAX_START_DELAY)
  onReconnect(background)
  document.addEventListener('visibilitychange', background)
  // Another tab, or the settings, chose not to download any more.
  watch(offlineWindow, (days, previous) => {
    if (!days && previous) removeOfflineDownloads()
  })
}
