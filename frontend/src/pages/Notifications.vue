<template>
  <PageHeaderMobile class="sm:hidden" title="Notifications">
    <template #suffix>
      <Button
        v-if="canMarkAllAsRead"
        variant="ghost"
        icon="lucide-check-check"
        label="Mark all as read"
        :loading="markAllAsRead.loading"
        @click="confirmMarkAllAsRead"
      />
    </template>
  </PageHeaderMobile>
  <PageHeader class="hidden sm:flex">
    <Breadcrumbs :items="[{ label: 'Notifications', route: { name: 'Notifications' } }]" />
    <!-- The page's one action lives in the header, like "Add new" on Discussions. -->
    <div class="flex items-center gap-2">
      <Button
        v-if="canMarkAllAsRead"
        :loading="markAllAsRead.loading"
        @click="confirmMarkAllAsRead"
      >
        Mark all as read
      </Button>
    </div>
  </PageHeader>

  <div class="body-container" :style="{ '--toolbar-height': `${toolbarHeight}px` }">
    <!-- Sticky toolbar, bled out by the body-container padding so its background covers
         the gutters as rows scroll under it (the Search page does the same). Desktop:
         tabs left, filters right on one line. Phone: the filters take their own
         full-width line under the tabs and scroll sideways if they overflow. -->
    <div
      ref="toolbarEl"
      class="sticky top-0 z-30 -mx-3 flex flex-wrap items-center gap-3 bg-surface-base px-7 pb-3 pt-4 sm:-mx-5 sm:flex-nowrap sm:px-8 sm:pt-5"
    >
      <TabButtons class="shrink-0" :options="tabOptions" v-model="activeTab" />
      <!-- Filters earn their place once there is something to filter. -->
      <div
        v-if="showFilters"
        class="-mx-4 w-[calc(100%+2rem)] overflow-x-auto px-4 py-0.5 sm:mx-0 sm:ml-auto sm:w-auto sm:min-w-0 sm:px-0"
      >
        <NotificationFilters class="w-max" />
      </div>
    </div>

    <!-- The recap of an away stretch sits above the unread list, and only there: read
         rows have nothing to recap. -->
    <AwayCard
      v-if="activeTab === 'Unread' && awaySummary.data"
      class="mb-4"
      :summary="awaySummary.data"
      @changed="reloadAfterAwayCard"
      @read="markAsRead"
    />

    <template v-if="isInitialLoading">
      <ListRowSkeleton
        v-for="index in skeletonRowCount"
        :key="index"
        :show-separator="index < skeletonRowCount"
        label="Loading notification"
      />
    </template>

    <List
      v-else-if="notifications?.length"
      class="max-sm:list-gap-3 sm:list-gap-4 max-sm:list-row-px-4"
    >
      <!-- One group per local calendar day, newest first, header pinned while its rows
           scroll under it. Days with nothing in them do not appear. -->
      <ListGroup
        v-for="group in dayGroups"
        :key="group.day"
        :label="group.label"
        sticky
        class="[&>[data-slot=list-group-header]]:!top-[var(--toolbar-height)] [&>[data-slot=list-group-header]]:z-20 max-sm:[&>[data-slot=list-group-header]]:px-4 sm:[&>[data-slot=list-group-header]]:px-3"
      >
        <NotificationListRow
          v-for="notification in group.rows"
          :key="notification.name"
          :notification="notification"
          :title="notificationTargetTitle(notification)"
          @read="markAsRead"
        />
      </ListGroup>
    </List>

    <!-- No empty state while the away card is the whole inbox: the card is the content. -->
    <div v-else-if="!(activeTab === 'Unread' && awaySummary.data)">
      <!-- A single picked day with nothing in it still shows its label, so the empty
           state reads as "nothing on this day" rather than "nothing at all". -->
      <div
        v-if="singleDayLabel"
        class="flex h-8 items-center px-4 text-sm-medium text-ink-gray-5 sm:px-3"
      >
        {{ singleDayLabel }}
      </div>
      <div
        class="mx-4 rounded-4 border border-dashed border-outline-gray-2 px-6 py-12 text-center sm:mx-3"
      >
        <div class="mx-auto grid size-10 place-items-center rounded-4 bg-surface-gray-2">
          <span class="lucide-bell-check size-5 text-ink-gray-5" aria-hidden="true" />
        </div>
        <div class="mt-3 text-base-medium text-ink-gray-8">{{ emptyStateTitle }}</div>
        <div class="mt-1 text-base text-ink-gray-5">{{ emptyStateDescription }}</div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, onScopeDispose, ref, watch } from 'vue'
import { useElementSize, watchDebounced } from '@vueuse/core'
import {
  Button,
  PageHeader,
  PageHeaderMobile,
  TabButtons,
  Breadcrumbs,
  dayjs,
  dayjsLocal,
  dialog,
  useCall,
  useList,
  usePageMeta,
} from 'frappe-ui'
import { List, ListGroup } from 'frappe-ui/list'
import AwayCard from '@/components/AwayCard.vue'
import ListRowSkeleton from '@/components/ListRowSkeleton.vue'
import NotificationFilters from '@/components/NotificationFilters.vue'
import NotificationListRow from '@/components/NotificationListRow.vue'
import { awaySummary } from '@/data/away'
import {
  clearNotificationFilters,
  hasActiveNotificationFilters,
  notificationDateBounds,
  notificationFilters,
  notificationListFilters,
} from '@/data/notificationFilters'
import {
  type NotificationRow,
  onRemoteNotificationChange,
  rememberNotificationRows,
  unreadNotifications,
} from '@/data/notifications'
import { useSessionUser } from '@/data/users'

type ActiveTab = 'Unread' | 'Read'

// `last_event_at` is optional in the generated type but every row carries it: new rows
// are stamped on insert and older ones were backfilled from `creation` (see
// gp_notification/patches/backfill_last_event_at.py).

const activeTab = ref<ActiveTab>('Unread')

// The day headers pin just under the sticky toolbar, whose height depends on whether the
// filters wrapped onto their own line — so it is measured, not assumed.
const toolbarEl = ref<HTMLElement | null>(null)
// Border box: the day labels pin to the toolbar's bottom edge, padding included. The
// default content box leaves them 28px under it, hidden behind its background.
const { height: toolbarHeight } = useElementSize(toolbarEl, undefined, { box: 'border-box' })
const sessionUser = useSessionUser()

const notificationFields = [
  'name',
  'from_user',
  'message',
  'read',
  'type',
  // Ordering and display both read this: the latest event behind the row.
  'last_event_at',
  'event_count',
  'comment',
  'discussion',
  'poll',
  'task',
  'project',
  'team',
]

// True from a filter change until the next page of rows lands; the loading guard below
// reads it. Declared before the lists so their onSuccess can clear it.
const filtersChangedSinceLoad = ref(false)
watch(notificationFilters, () => (filtersChangedSinceLoad.value = true), { deep: true })

/**
 * The filters show only when the tab being looked at has five or more notifications,
 * counted regardless of the filters themselves: under that there is nothing worth
 * narrowing. The unread count is the badge's; the read count is asked for here. A filter
 * left in local storage is cleared when the row goes, or it would narrow the list
 * invisibly.
 */
const FILTERS_FROM = 5
const readNotificationCount = useCall<number>({
  url: '/api/v2/method/frappe.client.get_count',
  params: { doctype: 'GP Notification', filters: { to_user: sessionUser.name, read: 1 } },
  cacheKey: ['Read Notification Count', sessionUser.name],
})
const showFilters = computed(() => {
  const count = activeTab.value === 'Unread' ? unreadNotifications.data : readNotificationCount.data
  return (count ?? FILTERS_FROM) >= FILTERS_FROM
})
watch(showFilters, (shown) => {
  if (!shown && hasActiveNotificationFilters.value) clearNotificationFilters()
})

const unreadNotificationList = useNotificationList(0, 'Unread Notifications')
const readNotificationList = useNotificationList(1, 'Read Notifications')

// The rail badge and these lists read the same state, so they have to move together.
// Without this the badge would count a notification raised (or cleared from another tab)
// while this page is open, and the list beneath it would keep showing something else.
// `onRemoteNotificationChange` hands over only the events reporting a count this tab is not
// already showing, so its own writes — which reload these lists themselves — do not come
// back around as a second reload.
onScopeDispose(
  onRemoteNotificationChange(() => {
    unreadNotificationList.reload()
    readNotificationList.reload()
    // A stretch that ended while the page was open shows its card on this same reload.
    awaySummary.reload()
    readNotificationCount.reload()
  }),
)

function reloadAfterAwayCard() {
  awaySummary.reload()
  unreadNotifications.reload()
  unreadNotificationList.reload()
  readNotificationList.reload()
  readNotificationCount.reload()
}

const loadedNotifications = computed<NotificationRow[]>(() => [
  ...(unreadNotificationList.data ?? []),
  ...(readNotificationList.data ?? []),
])

const discussionTitles = useLinkedTitles('GP Discussion', () =>
  linkedIds(loadedNotifications.value, 'discussion'),
)
const pollTitles = useLinkedTitles('GP Poll', () => linkedIds(loadedNotifications.value, 'poll'))
const taskTitles = useLinkedTitles('GP Task', () => linkedIds(loadedNotifications.value, 'task'))

const markAllAsRead = useCall({
  // `useCall` takes the URL verbatim (unlike the legacy `resources` API, it does not
  // expand a dotted method path), so a relative one would POST to /g/<method> — which
  // the SPA route answers with its own HTML, 200 and all, marking nothing read.
  url: '/api/v2/method/gameplan.api.mark_all_notifications_as_read',
  method: 'POST',
  immediate: false,
  onSuccess() {
    unreadNotifications.reload()
    unreadNotificationList.reload()
    readNotificationList.reload()
    readNotificationCount.reload()
    // Its rows are read now, so the summary comes back empty and the card goes.
    awaySummary.reload()
  },
})

const canMarkAllAsRead = computed(
  () => activeTab.value === 'Unread' && Boolean(unreadNotificationList.data?.length),
)

const tabOptions: { value: ActiveTab; label: ActiveTab }[] = [
  { value: 'Unread', label: 'Unread' },
  { value: 'Read', label: 'Read' },
]

// Rows the away card is showing stay out of the unread list beneath it — one place per
// row. They join the list when the card is dismissed (the summary turns null).
const rowsInAwayCard = computed(() => {
  const summary = awaySummary.data
  if (!summary) return new Set<string>()
  return new Set(
    [...summary.mentions.items, ...summary.comments, ...summary.other].map((item) =>
      String(item.name),
    ),
  )
})
const notifications = computed(() => {
  if (activeTab.value !== 'Unread') return readNotificationList.data
  const rows = unreadNotificationList.data
  if (!rows || rowsInAwayCard.value.size === 0) return rows
  return rows.filter((row) => !rowsInAwayCard.value.has(String(row.name)))
})

// The list arrives newest-first by `last_event_at`; bucket it by the user's local calendar
// day, keeping that order. A day key like "2026-09-16" keeps the groups stable across
// reloads; the label is what the header shows.
const dayGroups = computed(() => {
  const groups: { day: string; label: string; rows: NotificationRow[] }[] = []
  for (const row of notifications.value ?? []) {
    const at = dayjsLocal(row.last_event_at)
    const day = at.format('YYYY-MM-DD')
    const last = groups[groups.length - 1]
    if (last && last.day === day) {
      last.rows.push(row)
    } else {
      groups.push({ day, label: dayLabel(at), rows: [row] })
    }
  }
  return groups
})

function dayLabel(at: ReturnType<typeof dayjsLocal>) {
  const today = dayjsLocal()
  if (at.isSame(today, 'day')) return `Today, ${at.format('D MMMM')}`
  if (at.isSame(today.subtract(1, 'day'), 'day')) return `Yesterday, ${at.format('D MMMM')}`
  return at.format(at.year() === today.year() ? 'D MMMM, dddd' : 'D MMMM YYYY, dddd')
}

// When exactly one day is picked and it is empty, its label still heads the empty state.
const singleDayLabel = computed(() => {
  const bounds = notificationDateBounds.value
  if (!bounds || bounds[0] !== bounds[1]) return null
  return dayLabel(dayjs(bounds[0]))
})

// Same guard as DiscussionList: without it the fetch's empty window renders the
// "You're caught up" box, which contradicts the unread badge that brought the user here.
// A cached list (`cacheKey`) fills `data` before the request settles, so the skeleton
// only shows on a genuinely cold load — and while a filter change is in flight, because
// the cache would otherwise show the previous filter's rows under the new filter's label.
const skeletonRowCount = 3
const activeList = computed(() =>
  activeTab.value === 'Unread' ? unreadNotificationList : readNotificationList,
)
const isInitialLoading = computed(
  () =>
    activeList.value.loading && (!activeList.value.data?.length || filtersChangedSinceLoad.value),
)

// With a filter on, an empty list means "nothing matches", not "nothing at all".
const emptyStateTitle = computed(() => {
  if (hasActiveNotificationFilters.value) return 'Nothing here'
  return activeTab.value === 'Unread' ? "You're caught up" : 'No read notifications'
})

const emptyStateDescription = computed(() => {
  if (hasActiveNotificationFilters.value) return 'No notifications match these filters.'
  return activeTab.value === 'Unread'
    ? 'New notifications will show up here.'
    : 'Notifications you have handled will collect here.'
})

function markAsRead(name: string) {
  // No `unreadNotificationList.reload()` here: `setValue` already re-runs its own list on
  // success. Asking for it twice aborted the first request, which left the abort error
  // parked in the list's `error` ref.
  unreadNotificationList.setValue.submit({ name, read: 1 }).then(() => {
    // The badge reload is what makes the echo of this write recognisable: once it lands,
    // the badge holds the same count the echo reports and the echo is dropped.
    unreadNotifications.reload()
    readNotificationList.reload()
    readNotificationCount.reload()
    // The row may also be in the away card; it leaves the card the same way.
    if (awaySummary.data) awaySummary.reload()
  })
}

function notificationTargetTitle(notification: NotificationRow) {
  if (notification.poll) return pollTitles.value.get(String(notification.poll))
  if (notification.discussion) return discussionTitles.value.get(String(notification.discussion))
  if (notification.task) return taskTitles.value.get(String(notification.task))
  return null
}

function linkedIds(notifications: NotificationRow[], field: 'discussion' | 'poll' | 'task') {
  // Sorted because order is meaningless to an `in` filter but not to `useList`, which
  // refetches whenever the request URL changes. Marking a notification read reorders the
  // list without changing which documents it points at; sorting keeps that a no-op.
  return [...new Set(notifications.map((row) => row[field]).filter(Boolean))].map(String).sort()
}

/**
 * Titles of the discussions, polls, and tasks the notifications point at.
 *
 * These used to be joined into the notification query itself
 * (`discussion.title as discussion_title`), which silently emptied the whole
 * list: frappe's list API LEFT JOINs the linked doctype but puts that doctype's
 * permission condition in the outer WHERE (`LinkTableField.apply_join` in
 * frappe/database/query.py), so a row whose link is NULL fails the condition and
 * disappears. Asking for multiple nullable linked titles therefore dropped
 * valid rows. This is fixed on upstream `develop` and `version-16-hotfix`, but
 * not `version-16`; keep the separate queries until the hotfix merges forward
 * and this bench moves to a frappe version that carries it.
 */
function useLinkedTitles(doctype: 'GP Discussion' | 'GP Poll' | 'GP Task', ids: () => string[]) {
  // `queryIds` only ever holds a settled, non-empty id set, and that is what the lookup is
  // keyed on. The unread and read lists resolve a beat apart, so the ids arrive in more than
  // one step: fetching on each step fired a query for the empty set on mount and then a
  // second query that aborted the first, and `useList` reports an aborted fetch as an error.
  const queryIds = ref<string[]>([])
  watchDebounced(
    computed(ids),
    (settledIds) => {
      if (settledIds.length) queryIds.value = settledIds
    },
    { debounce: 150 },
  )

  const list = useList<{ name: string; title: string }>({
    doctype,
    fields: ['name', 'title'],
    filters: () => ({ name: ['in', queryIds.value] }),
    limit: 100,
    // Nothing to look up until the notifications land; the first id set starts the request,
    // and an id set that repeats leaves the request URL unchanged, so it does not refetch.
    immediate: false,
  })
  return computed(() => new Map((list.data ?? []).map((doc) => [String(doc.name), doc.title])))
}

function confirmMarkAllAsRead() {
  dialog.danger({
    title: 'Mark all as read',
    message:
      'This clears every unread notification at once, so nothing is left flagged for you to come back to. You cannot undo this.',
    confirmLabel: 'Mark all as read',
    onConfirm: () => markAllAsRead.submit(),
  })
}

function useNotificationList(read: 0 | 1, cacheKey: string) {
  return useList<NotificationRow>({
    doctype: 'GP Notification',
    // A getter, so the list refetches as the page filters change (see notificationFilters.ts).
    filters: () => ({ to_user: sessionUser.name, read, ...notificationListFilters() }),
    fields: notificationFields,
    // `last_event_at` is the one timestamp that is right for both ordering and display. A
    // reaction or comment notification is a single row re-lit in place, so `creation` would
    // bury a freshly raised one at its original position; `modified` also moves when the row
    // is marked read and would date every read notification to the moment it was opened.
    orderBy: 'last_event_at desc',
    // The page has no pagination control, so the window has to be wide enough to hold a
    // realistic backlog. `useList.reload()` refetches at the current offset and appends,
    // which makes a "load more" button unsafe on a list that mark-as-read reloads.
    limit: 100,
    cacheKey,
    // Lets the socket handler recognise the echo of this tab's own writes (see
    // data/notifications.ts): a `notification_changed` event naming a row we already hold
    // at this `event_count` and `read` is not news.
    onSuccess(rows) {
      rememberNotificationRows(rows)
      filtersChangedSinceLoad.value = false
    },
  })
}

unreadNotifications.reload()
awaySummary.reload()
usePageMeta(() => ({ title: 'Notifications' }))
</script>
