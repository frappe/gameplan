import { reactive, watch } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import { call, dialog, toast } from 'frappe-ui'
import { delMany, get, getMany, keys, set, setMany, values } from 'idb-keyval'
import { isOnline, onReconnect } from './online'
import { session } from './session'
import { customEmojis } from './customEmojis'
import { isMobileViewport } from '@/utils/useIsMobile'
import { communityFeedKey, spaceFeedKey } from './discussions'
import {
  ACTIVITY_FIELDS,
  COMMENT_FIELDS,
  POLL_FIELDS,
  activitiesCacheKey,
  commentsCacheKey,
  pollsCacheKey,
} from './discussionTimeline'

/**
 * "Download for offline" (Settings > Preferences): keeps the discussions from joined spaces with
 * activity in the chosen window on this device, with their comments, activity and polls.
 *
 * Downloads are filed into the same IndexedDB entries frappe-ui's resources read (`doc:` for
 * documents, `["useList", ...cacheKey]` for lists), so a downloaded discussion opens offline
 * like a visited one and needs no second copy. frappe-ui has no public API to seed its cache,
 * hence the key formats below. Everything lives in the default idb-keyval store, so logout and
 * user switch (offline.ts) wipe it with the rest.
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
// Matches the server's page size (gameplan/offline_downloads.py).
const PAGE_SIZE = 20
// Images one sync may add. Already saved ones are skipped, so later syncs add only new ones.
const MAX_IMAGES = 300
// Background syncs only fetch what changed, but still cost an index query each; this keeps
// them to a few a day per device.
const SYNC_INTERVAL = 6 * 60 * 60 * 1000
// Spreads the first sync after load so a team opening the app together doesn't sync together.
const MAX_START_DELAY = 30 * 1000
// What a feed asks for in one page (useDiscussions' default limit), so a restored list holds
// as much as a fetched one.
const FEED_LIMIT = 50

interface Meta {
  user: string
  window: number
  /** Server time the last complete sync started; the next one asks for changes since. */
  since: string | null
  /** Discussions downloaded to this device. */
  names: string[]
  lastSyncedAt: number | null
  /** The last sync stopped before finishing, so the next one runs whenever it can. */
  incomplete: boolean
}

interface Bundle {
  discussions: Array<Record<string, unknown> & { name: string | number }>
  /** The same discussions in the shape the feeds list them. */
  rows: FeedRow[]
  comments: Record<string, Row[]>
  activities: Record<string, Row[]>
  polls: Record<string, Row[]>
  has_next_page: boolean
}

type Row = Record<string, unknown> & { name: string | number }

type FeedRow = Row & { project?: string | number; team?: string; last_post_at?: string }

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
  error: null as string | null,
})

let meta: Meta | null = null

async function readMeta(): Promise<Meta | null> {
  const stored = (await get(META_KEY).catch(() => null)) as Meta | undefined
  meta = stored?.user === session.user ? stored : null
  downloads.count = meta?.names.length ?? 0
  downloads.lastSyncedAt = meta?.lastSyncedAt ?? null
  return meta
}

async function writeMeta(next: Meta) {
  meta = next
  downloads.count = next.names.length
  downloads.lastSyncedAt = next.lastSyncedAt
  await set(META_KEY, next)
}

/**
 * Brings the device in line with the chosen window. Automatic runs are skipped when a sync
 * happened recently, on Data Saver, or while the tab is hidden; `manual` runs skip those checks.
 */
export async function syncOfflineDownloads({ manual = false } = {}): Promise<boolean> {
  if (!session.isLoggedIn) return false
  // A manual run (a new window picked) waits for the current one, then brings it up to date.
  if (inflight) {
    await inflight.catch(() => {})
    if (!manual) return false
  }
  inflight = sync(manual).finally(() => (inflight = null))
  return inflight
}

let inflight: Promise<boolean> | null = null

async function sync(manual: boolean): Promise<boolean> {
  const days = offlineWindow.value
  const current = meta ?? (await readMeta())

  if (!days) {
    if (current) await removeOfflineDownloads()
    return true
  }
  if (!isOnline.value) return false
  if (!manual) {
    if (document.visibilityState !== 'visible' || saveData()) return false
    const fresh = current?.window === days && !current.incomplete && current.lastSyncedAt
    if (fresh && Date.now() - fresh < SYNC_INTERVAL) return true
  }

  // One tab at a time; another tab already syncing covers this one.
  if (!navigator.locks) return runSync(days)
  return navigator.locks.request(LOCK_NAME, { ifAvailable: true }, (lock) =>
    lock ? runSync(days) : false,
  )
}

/**
 * Returns whether the sync finished. Losing the connection stops it; the next run fetches
 * whatever is still missing.
 */
async function runSync(days: OfflineWindow): Promise<boolean> {
  downloads.syncing = true
  downloads.error = null
  downloads.done = 0
  downloads.total = 0
  try {
    const previous = meta ?? (await readMeta())
    const onDevice = new Set(await cachedDiscussions())
    const visited = [...onDevice].filter((name) => !previous?.names.includes(name))
    const index = await call<{ discussions: string[]; revoked: string[]; synced_at: string }>(
      INDEX,
      { window_days: days, cached: visited },
    )
    const names = index.discussions
    const dropped = (previous?.names ?? []).filter((name) => !names.includes(name))
    await forgetDiscussions([...dropped, ...index.revoked])

    // Only what is really on the device counts as downloaded. A new window starts over.
    const sameWindow = previous?.window === days
    const stored = new Set(
      sameWindow ? previous.names.filter((name) => names.includes(name) && onDevice.has(name)) : [],
    )
    const base: Meta = {
      user: session.user!,
      window: days,
      since: sameWindow ? previous.since : null,
      names: [...stored],
      lastSyncedAt: sameWindow ? previous.lastSyncedAt : null,
      incomplete: true,
    }
    await writeMeta(base)

    const images = new Set<string>()
    const feedRows = new Map<string, FeedRow>()
    const fetchPage = async (params: Record<string, unknown>) => {
      const bundle = await call<Bundle>(BUNDLE, {
        window_days: days,
        fields: { comments: COMMENT_FIELDS, activities: ACTIVITY_FIELDS, polls: POLL_FIELDS },
        ...params,
      })
      await storeBundle(bundle)
      for (const row of bundle.rows ?? []) feedRows.set(String(row.name), row)
      for (const discussion of bundle.discussions) stored.add(String(discussion.name))
      for (const url of bundleImages(bundle)) images.add(url)
      await writeMeta({ ...base, names: [...stored] })
      return bundle
    }

    // Changes to what the device already holds.
    if (base.since && stored.size) {
      let start = 0
      let hasNext = true
      while (hasNext) {
        if (!isOnline.value) return false
        const bundle = await fetchPage({ since: base.since, start })
        start += bundle.discussions.length
        hasNext = bundle.has_next_page
        if (hasNext) await idle()
      }
    }

    // Everything not on the device yet: a first download, a space joined since the last sync,
    // or what an interrupted sync didn't reach.
    const missing = names.filter((name) => !stored.has(name))
    downloads.total = missing.length
    for (let i = 0; i < missing.length; i += PAGE_SIZE) {
      if (!isOnline.value) return false
      if (i) await idle()
      await fetchPage({ names: missing.slice(i, i + PAGE_SIZE) })
      downloads.done = Math.min(i + PAGE_SIZE, missing.length)
    }

    await storeFeeds(feedRows, new Set([...dropped, ...index.revoked]))

    const emojis = (customEmojis.data ?? []).map((emoji) => emoji.image).filter(Boolean)
    saveImages([...emojis, ...images].slice(0, MAX_IMAGES) as string[])

    await writeMeta({
      ...base,
      names: [...stored],
      since: index.synced_at,
      lastSyncedAt: Date.now(),
      incomplete: false,
    })
    return true
  } catch (error) {
    downloads.error = error instanceof Error ? error.message : String(error)
    throw error
  } finally {
    downloads.syncing = false
  }
}

async function storeBundle(bundle: Bundle) {
  const user = session.user!
  const entries: [string, string][] = []
  for (const discussion of bundle.discussions) {
    const name = String(discussion.name)
    entries.push([docKey('GP Discussion', name), JSON.stringify({ ...discussion, name })])
    entries.push(
      listEntry(commentsCacheKey('GP Discussion', name, user), bundle.comments[name]),
      listEntry(activitiesCacheKey('GP Discussion', name, user), bundle.activities[name]),
      listEntry(pollsCacheKey(name, user), bundle.polls[name]),
    )
  }
  await setMany(entries)
}

/**
 * Files the downloaded discussions into the lists the Space and community feeds read, so a
 * Space the device has never opened still lists them offline.
 *
 * Rows already cached are merged rather than replaced: a changes-only sync brings back only
 * what changed, and a feed opened online holds discussions from outside the window. Rows for
 * discussions this sync removed go, so a feed never offers what the device no longer has.
 */
async function storeFeeds(rows: Map<string, FeedRow>, removed: Set<string>) {
  const user = session.user!
  const fresh = new Map<string, FeedRow[]>()
  const collect = (key: string, row: FeedRow) => {
    const list = fresh.get(key)
    if (list) list.push(row)
    else fresh.set(key, [row])
  }
  for (const row of rows.values()) {
    if (row.project != null) collect(listKey(feedCacheKey(spaceFeedKey(row.project), user)), row)
    if (row.team) collect(listKey(feedCacheKey(communityFeedKey(row.team), user)), row)
  }

  const cachedFeeds = (await keys()).filter(
    (key): key is string => typeof key === 'string' && key.startsWith(FEED_KEY_PREFIX),
  )
  const targets = [...new Set([...fresh.keys(), ...cachedFeeds])]
  if (!targets.length) return

  const stored = await getMany(targets).catch(() => [])
  const entries: [string, string][] = []
  targets.forEach((key, index) => {
    const merged = new Map<string, FeedRow>()
    for (const row of parseRows(stored[index])) {
      if (!removed.has(String(row.name))) merged.set(String(row.name), row)
    }
    for (const row of fresh.get(key) ?? []) merged.set(String(row.name), row)
    const next = [...merged.values()]
      .sort((a, b) => String(b.last_post_at ?? '').localeCompare(String(a.last_post_at ?? '')))
      .slice(0, FEED_LIMIT)
    entries.push([key, JSON.stringify(next.map((row) => ({ ...row, name: String(row.name) })))])
  })
  await setMany(entries)
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

/** Discussions saved on this device, whether downloaded or from the user's own visits. */
async function cachedDiscussions() {
  const prefix = docKey('GP Discussion', '')
  return (await keys())
    .filter((key): key is string => typeof key === 'string' && key.startsWith(prefix))
    .map((key) => key.slice(prefix.length))
}

async function forgetDiscussions(names: string[]) {
  if (!names.length) return
  const user = session.user!
  const docKeys = names.map((name) => docKey('GP Discussion', name))
  const commentKeys = names.map((name) => listKey(commentsCacheKey('GP Discussion', name, user)))
  const stored = await getMany([...docKeys, ...commentKeys]).catch(() => [])
  await delMany([
    ...docKeys,
    ...commentKeys,
    ...names.map((name) => listKey(activitiesCacheKey('GP Discussion', name, user))),
    ...names.map((name) => listKey(pollsCacheKey(name, user))),
  ])

  // Their images go too, so a discussion the user lost access to leaves nothing behind,
  // except those something still on the device shows: the worker keeps one copy per URL.
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

// The service worker keeps the images (gameplan-sw.js); without one there's nowhere to put them.
function saveImages(urls: string[]) {
  if (urls.length) navigator.serviceWorker?.controller?.postMessage({ type: 'CACHE_IMAGES', urls })
}

function forgetImages(urls: string[]) {
  if (urls.length) navigator.serviceWorker?.controller?.postMessage({ type: 'FORGET_IMAGES', urls })
}

/** Deletes everything downloaded; a discussion opened again online is cached as usual. */
export async function removeOfflineDownloads() {
  const current = meta ?? (await readMeta())
  if (!current) return
  await forgetDiscussions(current.names)
  await delMany([META_KEY])
  meta = null
  downloads.count = 0
  downloads.lastSyncedAt = null
}

/** Picks a window and downloads it now, with a toast for the foreground download. */
export function downloadForOffline(days: OfflineWindow) {
  offlineWindow.value = days
  if (!days) return removeOfflineDownloads()
  // Without this the browser may evict the downloads under storage pressure (Safari does
  // after a week of not opening the site).
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

// The key formats frappe-ui's useList and docStore use for IndexedDB.
function listKey(cacheKey: unknown[]) {
  return JSON.stringify(['useList', ...cacheKey])
}

// Per user, like every feed's own key (data/discussions.ts).
function feedCacheKey(key: string, user: string) {
  return ['Discussions', key, user]
}

const FEED_KEY_PREFIX = '["useList","Discussions"'

function docKey(doctype: string, name: string) {
  return `doc:${doctype}/${name}`
}

function listEntry(cacheKey: unknown[], rows: Row[] = []): [string, string] {
  // Raw rows, names as strings like useList stores them; each list applies its own transform
  // when it reads the cache.
  return [
    listKey(cacheKey),
    JSON.stringify(rows.map((row) => ({ ...row, name: String(row.name) }))),
  ]
}

function saveData() {
  return Boolean(
    (navigator as Navigator & { connection?: { saveData?: boolean } }).connection?.saveData,
  )
}

function idle() {
  return new Promise<void>((resolve) =>
    'requestIdleCallback' in window
      ? requestIdleCallback(() => resolve(), { timeout: 2000 })
      : setTimeout(resolve, 200),
  )
}

/** Starts background syncing: once shortly after load, then on reconnect and when the tab returns. */
export function setupOfflineDownloads() {
  const background = () => syncOfflineDownloads().catch(() => {})
  readMeta()
  setTimeout(background, 5000 + Math.random() * MAX_START_DELAY)
  onReconnect(background)
  document.addEventListener('visibilitychange', background)
  watch(offlineWindow, (days, previous) => {
    if (!days && previous) removeOfflineDownloads()
  })
  setupIntroduction()
}

const introduction = useLocalStorage<'new' | 'seen-offline' | 'done'>(
  `gameplan:offline-intro:${session.user}`,
  'new',
)

/**
 * Introduces downloads once per device: a toast the first time the connection drops (nothing
 * can be downloaded then), and an offer to download on the next app load. Not on reconnect,
 * where a dialog would land on top of whatever the person was in the middle of.
 */
function setupIntroduction() {
  watch(isOnline, (online) => {
    if (online || offlineWindow.value || introduction.value !== 'new') return
    introduction.value = 'seen-offline'
    toast.info("You're offline. Only discussions you've opened are available.", {
      action: { label: 'Set up offline reading', onClick: openOfflineSettings },
    })
  })
  if (introduction.value === 'seen-offline') setTimeout(offerDownload, 3000)
}

function offerDownload() {
  if (offlineWindow.value || !isOnline.value) return
  introduction.value = 'done'
  const settings = isMobileViewport() ? 'More > Offline' : 'Settings > Preferences'
  dialog.confirm({
    title: 'Read Gameplan offline',
    message: `Keep discussions from the past month in your Spaces on this device, so they open even without a connection. You can change this in ${settings}.`,
    confirmLabel: 'Download',
    cancelLabel: 'Not now',
    onConfirm: () => {
      downloadForOffline(30)
    },
  })
}

function openOfflineSettings() {
  // Imported on demand: the settings module and the router both reach this module.
  if (isMobileViewport()) {
    import('@/router').then(({ default: router }) => router.push({ name: 'OfflineSettings' }))
  } else {
    import('@/components/Settings').then(({ showSettingsDialog }) =>
      showSettingsDialog('Preferences'),
    )
  }
}
