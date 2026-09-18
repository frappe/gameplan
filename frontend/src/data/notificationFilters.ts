import { computed } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import { dayjs, dayjsLocal, getConfig } from 'frappe-ui'

/**
 * The inbox's date filter. `range` bounds are `YYYY-MM-DD` in the user's local calendar,
 * inclusive on both ends; a single day is a range whose ends are the same date.
 */
export type NotificationDateFilter =
  | { kind: 'all' }
  | { kind: 'today' }
  | { kind: 'range'; from: string; to: string }

export interface NotificationFilterState {
  communities: string[]
  spaces: string[]
  date: NotificationDateFilter
}

const defaultFilters: NotificationFilterState = {
  communities: [],
  spaces: [],
  date: { kind: 'all' },
}

/**
 * Persisted per browser so a reload keeps the view the user set up. Per-viewer
 * convenience only — nothing here is state the server needs.
 */
const stored = useLocalStorage<NotificationFilterState>('gameplan:notificationFilters', {
  ...defaultFilters,
})

export const notificationFilters = computed({
  get: () => normalize(stored.value),
  set: (value: NotificationFilterState) => {
    stored.value = normalize(value)
  },
})

export function setNotificationCommunities(communities: string[]) {
  notificationFilters.value = { ...notificationFilters.value, communities }
}

export function setNotificationSpaces(spaces: string[]) {
  notificationFilters.value = { ...notificationFilters.value, spaces }
}

export function setNotificationDate(date: NotificationDateFilter) {
  notificationFilters.value = { ...notificationFilters.value, date }
}

export function clearNotificationFilters() {
  notificationFilters.value = { ...defaultFilters }
}

export const hasActiveNotificationFilters = computed(() => {
  const { communities, spaces, date } = notificationFilters.value
  return communities.length > 0 || spaces.length > 0 || date.kind !== 'all'
})

/**
 * The local calendar days the date filter covers, as `[from, to]` in `YYYY-MM-DD`, or
 * null for "all". Today resolves at read time so a tab left open overnight moves on.
 */
export const notificationDateBounds = computed<[string, string] | null>(() => {
  const date = notificationFilters.value.date
  if (date.kind === 'all') return null
  if (date.kind === 'today') {
    const today = dayjsLocal().format('YYYY-MM-DD')
    return [today, today]
  }
  return [date.from, date.to]
})

/**
 * The list filters the inbox query needs on top of `to_user` and `read`.
 *
 * Frappe stores datetimes in the site's system timezone, so the user's local day
 * boundaries are converted to system time (`toSystem`) before they go into the `between`.
 * Community and space are plain `in` filters on the row's own `team` / `project`; a row
 * without a space (added to a community, discussion since deleted) only ever matches
 * when no space is picked.
 */
export function notificationListFilters(): Record<string, unknown> {
  const { communities, spaces } = notificationFilters.value
  const filters: Record<string, unknown> = {}
  if (communities.length) filters.team = ['in', communities]
  if (spaces.length) filters.project = ['in', spaces]
  const bounds = notificationDateBounds.value
  if (bounds) {
    const [from, to] = bounds
    filters.last_event_at = ['between', [toSystem(`${from} 00:00:00`), toSystem(`${to} 23:59:59`)]]
  }
  return filters
}

/**
 * A local-time string in the site's system timezone — the inverse of `dayjsLocal`.
 *
 * frappe-ui has this as `dayjsSystem` in src/utils/dayjs.ts but does not export it from
 * its index yet; this is that function, line for line, until the export lands upstream
 * (frappe/frappe-ui: export dayjsSystem alongside dayjsLocal). Drop it then.
 */
function toSystem(localDateTime: string) {
  const systemTimezone = getConfig('systemTimezone')
  const localTimezone =
    getConfig('localTimezone') || Intl.DateTimeFormat().resolvedOptions().timeZone
  const at = systemTimezone
    ? dayjs.tz(localDateTime, localTimezone).tz(systemTimezone)
    : dayjs(localDateTime)
  return at.format('YYYY-MM-DD HH:mm:ss')
}

function normalize(value: Partial<NotificationFilterState> | null | undefined) {
  const communities = Array.isArray(value?.communities) ? value.communities.map(String) : []
  const spaces = Array.isArray(value?.spaces) ? value.spaces.map(String) : []
  const date = normalizeDate(value?.date)
  return { communities, spaces, date }
}

function normalizeDate(date: unknown): NotificationDateFilter {
  if (!date || typeof date !== 'object') return { kind: 'all' }
  const candidate = date as Partial<{ kind: string; from: string; to: string }>
  if (candidate.kind === 'today') return { kind: 'today' }
  if (candidate.kind === 'range' && isDate(candidate.from) && isDate(candidate.to)) {
    return candidate.from <= candidate.to
      ? { kind: 'range', from: candidate.from, to: candidate.to }
      : { kind: 'range', from: candidate.to, to: candidate.from }
  }
  return { kind: 'all' }
}

function isDate(value: unknown): value is string {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
}
