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
    <div
      ref="toolbarEl"
      class="sticky top-0 z-30 -mx-3 flex flex-wrap items-center gap-3 bg-surface-base px-7 pb-3 pt-4 sm:-mx-5 sm:flex-nowrap sm:px-8 sm:pt-5"
    >
      <TabButtons class="shrink-0" :options="tabOptions" v-model="activeTab" />
      <div
        v-if="showFilters"
        class="-mx-4 w-[calc(100%+2rem)] overflow-x-auto px-4 py-0.5 sm:mx-0 sm:ml-auto sm:w-auto sm:min-w-0 sm:px-0"
      >
        <NotificationFilters class="w-max" />
      </div>
    </div>

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

    <div v-else>
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
import ListRowSkeleton from '@/components/ListRowSkeleton.vue'
import NotificationFilters from '@/components/NotificationFilters.vue'
import NotificationListRow from '@/components/NotificationListRow.vue'
import {
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

const activeTab = ref<ActiveTab>('Unread')

const toolbarEl = ref<HTMLElement | null>(null)
const { height: toolbarHeight } = useElementSize(toolbarEl, undefined, { box: 'border-box' })
const sessionUser = useSessionUser()

const notificationFields = [
  'name',
  'from_user',
  'message',
  'read',
  'type',
  'last_event_at',
  'event_count',
  'comment',
  'discussion',
  'poll',
  'task',
  'project',
  'team',
]

const filtersChangedSinceLoad = ref(false)
watch(notificationFilters, () => (filtersChangedSinceLoad.value = true), { deep: true })

const FILTERS_FROM = 5
const readNotificationCount = useCall<number>({
  url: '/api/v2/method/frappe.client.get_count',
  params: {
    doctype: 'GP Notification',
    filters: JSON.stringify({ to_user: sessionUser.name, read: 1 }),
  },
  cacheKey: ['Read Notification Count', sessionUser.name],
})
const showFilters = computed(() => {
  if (hasActiveNotificationFilters.value) return true
  const count = activeTab.value === 'Unread' ? unreadNotifications.data : readNotificationCount.data
  return (count ?? FILTERS_FROM) >= FILTERS_FROM
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
    readNotificationCount.reload()
  }),
)

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
  },
})

const canMarkAllAsRead = computed(
  () => activeTab.value === 'Unread' && Boolean(unreadNotificationList.data?.length),
)

const tabOptions: { value: ActiveTab; label: ActiveTab }[] = [
  { value: 'Unread', label: 'Unread' },
  { value: 'Read', label: 'Read' },
]

const notifications = computed(() =>
  activeTab.value === 'Unread' ? unreadNotificationList.data : readNotificationList.data,
)

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

const singleDayLabel = computed(() => {
  const bounds = notificationDateBounds.value
  if (!bounds || bounds[0] !== bounds[1]) return null
  return dayLabel(dayjs(bounds[0]))
})

// Same guard as DiscussionList: without it the fetch's empty window renders the
// "You're caught up" box, which contradicts the unread badge that brought the user here.
// A cached list (`cacheKey`) fills `data` before the request settles, so the skeleton
const skeletonRowCount = 3
const activeList = computed(() =>
  activeTab.value === 'Unread' ? unreadNotificationList : readNotificationList,
)
const isInitialLoading = computed(
  () =>
    activeList.value.loading && (!activeList.value.data?.length || filtersChangedSinceLoad.value),
)

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
    filters: () => ({ to_user: sessionUser.name, read, ...notificationListFilters() }),
    fields: notificationFields,
    orderBy: 'last_event_at desc',
    // The page has no pagination control, so the window has to be wide enough to hold a
    // realistic backlog. `useList.reload()` refetches at the current offset and appends,
    // which makes a "load more" button unsafe on a list that mark-as-read reloads.
    limit: 100,
    cacheKey,
    onSuccess(rows) {
      rememberNotificationRows(rows)
      filtersChangedSinceLoad.value = false
    },
  })
}

unreadNotifications.reload()
usePageMeta(() => ({ title: 'Notifications' }))
</script>
