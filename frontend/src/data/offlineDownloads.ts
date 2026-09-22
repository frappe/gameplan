import { reactive, watch } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import { call, dialog, toast } from 'frappe-ui'
import { delMany, get, getMany, keys, set, setMany, values } from 'idb-keyval'
import { isOnline, onReconnect, saveData } from './online'
import { session } from './session'
import { customEmojis } from './customEmojis'
import { isMobileViewport } from '@/utils/useIsMobile'
import { OFFLINE_ACTION_MESSAGE } from './loadFailure'
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
// Matches the server's per-device cap (MAX_DISCUSSIONS there): on a busy site the window
// holds far more than this, and the device keeps the newest slice of it.
export const MAX_DISCUSSIONS = 500
// Images one sync may add. Already saved ones are skipped, so later syncs add only new ones.
const MAX_IMAGES = 300
// Background syncs only fetch what changed, but still cost an index query each; this keeps
// them to a few a day per device.
const SYNC_INTERVAL = 6 * 60 * 60 * 1000
// Spreads the first sync after load so a team opening the app together doesn't sync together.
const MAX_START_DELAY = 30 * 1000
// Visited discussions one index call can check for lost access (MAX_CACHED in
// offline_downloads.py). A device holding more walks them a slice at a time.
const VISIT_CHECK_LIMIT = 2000
// What a feed asks for in one page (useDiscussions' default limit), so a restored list holds
// as much as a fetched one.
const FEED_LIMIT = 50

interface Meta {
  user: string
  window: number
  /** Server time the last complete sync started; the next one asks for changes since. */
  since: string | null
  /** Discussions downloaded to this device, each with where the index said it sat. */
  places: Record<string, string>
  /** How far the last sync got through checking visited discussions for lost access. */
  checkedUpTo?: string
  lastSyncedAt: number | null
  /** The last sync stopped before finishing, so the next one runs whenever it can. */
  incomplete: boolean
}

interface Index {
  discussions: string[]
  /** Where each of them sits now, so one that moved Space or community is fetched again. */
  places: Record<string, string>
  /** Changed since the device's last complete sync, so only these are fetched again. */
  changed: string[]
  revoked: string[]
  synced_at: string
}

interface Bundle {
  discussions: Array<Record<string, unknown> & { name: string | number }>
  /** The same discussions in the shape the feeds list them. */
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

/** A cached feed this sync maintains: which rows belong in it, and how they are ordered. */
interface Feed {
  key: string
  space?: string
  community?: string
  pinned: boolean
  /** Unread and Participating: which of a community's discussions they hold is the server's
   * answer, not something a download can work out, so a sync only takes rows out of them. */
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
  error: null as string | null,
})

let meta: Meta | null = null
let removal: Promise<void> | null = null

async function readMeta(): Promise<Meta | null> {
  const stored = (await get(META_KEY).catch(() => null)) as Meta | undefined
  // A record from before places were kept starts over rather than syncing against nothing.
  meta = stored?.user === session.user && stored.places ? stored : null
  downloads.count = meta ? Object.keys(meta.places).length : 0
  downloads.lastSyncedAt = meta?.lastSyncedAt ?? null
  return meta
}

async function writeMeta(next: Meta) {
  meta = next
  downloads.count = Object.keys(next.places).length
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
    if (document.visibilityState !== 'visible' || saveData.value) return false
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
    const downloaded = previous?.places ?? {}
    const visits = visitsToCheck(
      [...onDevice].filter((name) => !(name in downloaded)),
      previous?.checkedUpTo,
    )
    const sameWindow = previous?.window === days
    const index = await call<Index>(INDEX, {
      window_days: days,
      cached: visits.names,
      since: sameWindow ? previous.since : null,
    })
    const names = new Set(index.discussions)
    const dropped = Object.keys(downloaded).filter((name) => !names.has(name))
    await forgetDiscussions([...dropped, ...index.revoked])

    // Only what is really on the device counts as downloaded. A new window starts over.
    const places: Record<string, string> = {}
    for (const name of sameWindow ? Object.keys(downloaded) : []) {
      if (names.has(name) && onDevice.has(name)) places[name] = downloaded[name]
    }
    const base: Meta = {
      user: session.user!,
      window: days,
      since: sameWindow ? previous.since : null,
      places,
      checkedUpTo: visits.checkedUpTo,
      lastSyncedAt: sameWindow ? previous.lastSyncedAt : null,
      incomplete: true,
    }
    await writeMeta(base)

    const images = new Set<string>()
    const feedRows = new Map<string, FeedRow>()
    const fetchPage = async (names: string[]) => {
      const bundle = await call<Bundle>(BUNDLE, {
        window_days: days,
        fields: { comments: COMMENT_FIELDS, activities: ACTIVITY_FIELDS, polls: POLL_FIELDS },
        names,
      })
      await storeBundle(bundle)
      for (const row of bundle.rows ?? []) feedRows.set(String(row.name), row)
      for (const discussion of bundle.discussions) {
        const name = String(discussion.name)
        places[name] = index.places[name]
      }
      for (const url of bundleImages(bundle)) images.add(url)
      await writeMeta({ ...base, places: { ...places } })
    }

    // What the index says changed, plus everything filed somewhere other than where the
    // index now places it: not held at all (a first download, a Space that joined the window
    // since, what an interrupted sync missed), or moved to another Space or community.
    const changed = new Set(index.changed)
    const wanted = index.discussions.filter(
      (name) => changed.has(name) || places[name] !== index.places[name],
    )
    downloads.total = wanted.length
    for (let i = 0; i < wanted.length; i += PAGE_SIZE) {
      if (!isOnline.value) return false
      if (i) await idle()
      await fetchPage(wanted.slice(i, i + PAGE_SIZE))
      downloads.done = Math.min(i + PAGE_SIZE, wanted.length)
    }

    await storeFeeds(feedRows, new Set([...dropped, ...index.revoked]))

    const emojis = (customEmojis.data ?? []).map((emoji) => emoji.image).filter(Boolean)
    saveImages([...emojis, ...images].slice(0, MAX_IMAGES) as string[])

    await writeMeta({
      ...base,
      places: { ...places },
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

/**
 * The visited discussions this sync asks about, and the name the next one resumes after.
 *
 * One request can only check so many, so a device holding more than that walks them in name
 * order across syncs: asking about the same first names every time would leave everything
 * past them never checked, and a discussion the user lost access to still readable offline.
 */
function visitsToCheck(names: string[], after = '') {
  if (names.length <= VISIT_CHECK_LIMIT) return { names, checkedUpTo: '' }
  const sorted = [...names].sort()
  // Resume after the last name checked, starting over once past the end.
  const found = sorted.findIndex((name) => name > after)
  const start = found === -1 ? 0 : found
  const slice = sorted.slice(start, start + VISIT_CHECK_LIMIT)
  return { names: slice, checkedUpTo: slice[slice.length - 1] }
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
  if (!rows.size && !removed.size) return
  const user = session.user!
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
  for (const feed of [...downloadedFeeds(rows.values(), user), ...(await cachedFeeds(user))]) {
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
      // A discussion that moved Space comes back filed under the new one, so the feed it
      // left has to let it go rather than list it in both.
      if (removed.has(name) || (fresh && !belongsTo(fresh, feed))) continue
      merged.set(name, fresh ?? row)
    }
    for (const row of candidates) {
      if (belongsTo(row, feed)) merged.set(String(row.name), row)
    }

    // Keep whatever the feed already held: a list someone paged through online holds more
    // than one page, and dropping the rest would lose them offline.
    const limit = feed.pinned ? Infinity : Math.max(FEED_LIMIT, parseRows(stored[index]).length)
    const order = feed.pinned ? 'pinned_at' : 'last_post_at'
    const next = [...merged.values()]
      .sort((a, b) => String(b[order] ?? '').localeCompare(String(a[order] ?? '')))
      .slice(0, limit)
      .map((row) => ({ ...row, name: String(row.name) }))

    const value = JSON.stringify(next)
    // Feeds this sync never touched are left alone; a busy site has a lot of them.
    if (value !== stored[index]) entries.push([feed.key, value])
  })
  if (entries.length) await setMany(entries)
}

/** The feeds a downloaded row belongs to, whether or not the device has opened them. */
function downloadedFeeds(rows: Iterable<FeedRow>, user: string): Feed[] {
  const feeds = new Map<string, Feed>()
  const add = (key: string, feed: Omit<Feed, 'key'>) => feeds.set(key, { ...feed, key })
  for (const row of rows) {
    const space = row.project == null ? null : String(row.project)
    if (space) {
      add(listKey(feedCacheKey(spaceFeedKey(space), user)), { space, pinned: false })
      if (row.pinned_at) {
        add(listKey(feedCacheKey(['pinned', spaceFeedKey(space)], user)), { space, pinned: true })
      }
    }
    if (row.team) {
      add(listKey(feedCacheKey(communityFeedKey(row.team), user)), {
        community: row.team,
        pinned: false,
      })
      if (row.pinned_at) {
        add(listKey(feedCacheKey(['pinned', communityFeedKey(row.team)], user)), {
          community: row.team,
          pinned: true,
        })
      }
    }
  }
  return [...feeds.values()]
}

/** Feeds this user has already cached, so rows that moved or went away leave them too. */
async function cachedFeeds(user: string): Promise<Feed[]> {
  const feeds: Feed[] = []
  for (const key of await keys()) {
    if (typeof key !== 'string' || !key.startsWith(FEED_KEY_PREFIX)) continue
    let parts: unknown[]
    try {
      parts = JSON.parse(key)
    } catch {
      continue
    }
    // Another account's feeds on this browser are not ours to rewrite.
    if (parts[parts.length - 1] !== user) continue
    const inner = parts[2]
    const pinned = Array.isArray(inner) && inner[0] === 'pinned'
    const name = pinned ? inner[1] : inner
    const scope = typeof name === 'string' ? feedScope(name) : null
    if (!scope) continue
    const { space, community, feedType } = scope
    feeds.push({
      key,
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

/**
 * Deletes everything downloaded; a discussion opened again online is cached as usual.
 *
 * The settings button and the window watcher below both ask for this on the same click, and
 * another tab turning downloads off adds a third. One run does the work, scanning the device
 * for images still in use once rather than once per caller; the rest wait on it.
 */
export function removeOfflineDownloads(): Promise<void> {
  removal ??= removeEverything().finally(() => (removal = null))
  return removal
}

async function removeEverything() {
  const current = meta ?? (await readMeta())
  if (!current) return
  await forgetDiscussions(Object.keys(current.places))
  await delMany([META_KEY])
  meta = null
  downloads.count = 0
  downloads.lastSyncedAt = null
}

/** Picks a window and downloads it now, with a toast for the foreground download. */
export function downloadForOffline(days: OfflineWindow) {
  // The controls that start one are disabled offline, but a dialog already open when the
  // connection drops is not, and the window must not move to one nothing was fetched for.
  if (days && !isOnline.value) {
    toast.warning(OFFLINE_ACTION_MESSAGE, { id: 'offline-action' })
    return
  }
  offlineWindow.value = days
  // Removing what is on the device needs no connection.
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
function feedCacheKey(key: string | string[], user: string) {
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
      action: { label: 'Set up', onClick: openOfflineSettings },
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
      openOfflineSettings()
    },
  })
}

/** Anchor for the Offline section of Settings > Preferences, which opens scrolled to it. */
export const OFFLINE_SECTION_ID = 'offline-settings'

function openOfflineSettings() {
  // Imported on demand: the settings module and the router both reach this module.
  if (isMobileViewport()) {
    import('@/router').then(({ default: router }) => router.push({ name: 'OfflineSettings' }))
  } else {
    import('@/components/Settings').then(({ showSettingsDialog }) => {
      showSettingsDialog('Preferences')
      // Offline is the last section of a scrolling tab, so opening it is not enough.
      scrollToOfflineSection()
    })
  }
}

function scrollToOfflineSection(attemptsLeft = 20) {
  const section = document.getElementById(OFFLINE_SECTION_ID)
  if (section) {
    section.scrollIntoView({ block: 'start', behavior: 'smooth' })
    return
  }
  if (attemptsLeft) requestAnimationFrame(() => scrollToOfflineSection(attemptsLeft - 1))
}
