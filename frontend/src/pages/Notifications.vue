<template>
  <PageHeaderMobile class="sm:hidden" title="Notifications" />
  <PageHeader class="hidden sm:flex">
    <Breadcrumbs :items="[{ label: 'Notifications', route: { name: 'Notifications' } }]" />
  </PageHeader>

  <div class="body-container pt-4 sm:pt-5">
    <div class="mb-3 flex items-center justify-between px-4 sm:px-3 gap-3">
      <TabButtons :buttons="tabButtons" v-model="activeTab" />
      <Button
        @click="confirmMarkAllAsRead"
        :loading="markAllAsRead.loading"
        v-if="canMarkAllAsRead"
      >
        Mark all as read
      </Button>
    </div>

    <List v-if="notifications?.length" class="max-sm:list-gap-3 sm:list-gap-4 max-sm:list-row-px-4">
      <ListRow
        v-for="notification in notifications"
        :key="notification.name"
        :to="notificationRoute(notification) ?? undefined"
        class="group h-[68px] sm:h-15"
        :class="!notification.read && 'w-[calc(100%-2.5rem)]'"
        @click="openNotification(notification)"
      >
        <ListCell>
          <UserAvatarWithHover
            size="2xl"
            :user="notification.from_user"
            v-if="showAvatar(notification)"
          />
          <div
            class="grid size-10 place-items-center rounded-[8px] bg-surface-gray-2 group-hover:bg-surface-base"
            v-else
          >
            <ReactionFaceIcon
              class="size-5 text-ink-gray-6"
              v-if="notification.type === 'Reaction'"
            />
            <span
              :class="[notificationIcon(notification), 'size-5 text-ink-gray-6']"
              aria-hidden="true"
              v-else
            />
          </div>
        </ListCell>
        <ListCell>
          <div class="min-w-0 flex-1">
            <div class="flex min-w-0 items-center">
              <div
                class="overflow-hidden text-ellipsis whitespace-nowrap leading-none text-ink-gray-8"
              >
                <span
                  class="overflow-hidden text-ellipsis whitespace-nowrap"
                  :class="
                    notification.read
                      ? 'text-lg sm:text-base'
                      : 'text-lg-medium sm:text-base-medium'
                  "
                >
                  {{ notification.message }}
                </span>
              </div>
            </div>

            <div class="mt-1.5 flex min-w-0 items-center justify-between">
              <div
                class="inline-flex items-center overflow-hidden text-ellipsis whitespace-nowrap text-md text-ink-gray-5 sm:text-base"
              >
                <div class="flex min-w-0 items-center" v-if="notificationTargetTitle(notification)">
                  <div class="truncate">
                    {{ notificationTargetTitle(notification) }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </ListCell>
        <ListCell class="justify-end">
          <div>
            <!-- `creation`, not `modified`: marking a notification read is a PUT that bumps
                 `modified`, so a Monday mention opened on Thursday would claim to be "a few
                 seconds ago" for the rest of its life. The list is still ordered by
                 `modified` so a re-lit notification resurfaces (see useNotificationList),
                 which can read slightly out of order here — an honest timestamp out of order
                 beats a wrong one in order. -->
            <time
              class="block shrink-0 whitespace-nowrap text-right text-sm text-ink-gray-5"
              :datetime="notification.creation"
            >
              <span class="sm:hidden">{{ shortTimestamp(notification.creation) }}</span>
              <span class="hidden sm:inline">
                {{ dayjsLocal(notification.creation).fromNow() }}
              </span>
            </time>
            <div
              class="mt-1.5 hidden whitespace-nowrap text-right text-sm text-ink-gray-5 sm:block"
              v-if="notificationLocation(notification)"
            >
              {{ notificationLocation(notification) }}
            </div>
          </div>
        </ListCell>
        <!-- Sits in the 2.5rem gutter the unread row's reduced width leaves free.
             stop+prevent keep the click from bubbling into row navigation. -->
        <div class="absolute -right-10 top-1/2 z-10 -translate-y-1/2" v-if="!notification.read">
          <Tooltip text="Mark as read">
            <Button
              variant="subtle"
              icon="lucide-check"
              @click.stop.prevent="markAsRead(notification.name)"
            />
          </Tooltip>
        </div>
      </ListRow>
    </List>

    <div
      v-else
      class="mx-4 rounded-4 border border-dashed border-outline-gray-2 px-6 py-12 text-center sm:mx-3"
    >
      <div class="mx-auto grid size-10 place-items-center rounded-4 bg-surface-gray-2">
        <span class="lucide-bell-check size-5 text-ink-gray-5" aria-hidden="true" />
      </div>
      <div class="mt-3 text-base-medium text-ink-gray-8">{{ emptyStateTitle }}</div>
      <div class="mt-1 text-base text-ink-gray-5">{{ emptyStateDescription }}</div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, onScopeDispose, ref } from 'vue'
import { watchDebounced } from '@vueuse/core'
import type { RouteLocationRaw } from 'vue-router'
import {
  PageHeader,
  PageHeaderMobile,
  TabButtons,
  Tooltip,
  Breadcrumbs,
  dayjsLocal,
  dialog,
  useCall,
  useList,
  usePageMeta,
} from 'frappe-ui'
import { List, ListRow, ListCell } from 'frappe-ui/list'
import ReactionFaceIcon from '@/components/ReactionFaceIcon.vue'
import UserAvatarWithHover from '@/components/UserAvatarWithHover.vue'
import { getCommunity } from '@/data/communities'
import { onRemoteNotificationChange, unreadNotifications } from '@/data/notifications'
import { getSpace } from '@/data/spaces'
import { useSessionUser } from '@/data/users'
import type { GPNotification } from '@/types/doctypes'

type ActiveTab = 'Unread' | 'Read'

type NotificationRow = GPNotification

const activeTab = ref<ActiveTab>('Unread')
const sessionUser = useSessionUser()

const notificationFields = [
  'name',
  'from_user',
  'message',
  'read',
  'type',
  'creation',
  // Not displayed — it is what the list is ordered by.
  'modified',
  'comment',
  'discussion',
  'poll',
  'task',
  'project',
  'team',
]

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
  },
})

const canMarkAllAsRead = computed(
  () => activeTab.value === 'Unread' && Boolean(unreadNotificationList.data?.length),
)

const tabButtons: { label: ActiveTab }[] = [{ label: 'Unread' }, { label: 'Read' }]

const notifications = computed(() =>
  activeTab.value === 'Unread' ? unreadNotificationList.data : readNotificationList.data,
)

const emptyStateTitle = computed(() =>
  activeTab.value === 'Unread' ? "You're caught up" : 'No read notifications',
)

const emptyStateDescription = computed(() =>
  activeTab.value === 'Unread'
    ? 'New notifications will show up here.'
    : 'Notifications you have handled will collect here.',
)

function openNotification(notification: NotificationRow) {
  if (!notification.read && notificationRoute(notification)) {
    markAsRead(notification.name)
  }
}

function markAsRead(name: string) {
  // No `unreadNotificationList.reload()` here: `setValue` already re-runs its own list on
  // success. Asking for it twice aborted the first request, which left the abort error
  // parked in the list's `error` ref.
  unreadNotificationList.setValue.submit({ name, read: 1 }).then(() => {
    // The badge reload is what makes the echo of this write recognisable: once it lands,
    // the badge holds the same count the echo reports and the echo is dropped.
    unreadNotifications.reload()
    readNotificationList.reload()
  })
}

function notificationRoute(notification: NotificationRow): RouteLocationRaw | null {
  if (notification.discussion) {
    return {
      name: 'Discussion',
      params: {
        communityId: notification.team,
        spaceId: notification.project,
        postId: notification.discussion,
      },
      query: notification.poll
        ? { poll: notification.poll }
        : notification.comment
          ? { comment: notification.comment }
          : undefined,
    }
  }
  if (notification.task) {
    return {
      name: 'SpaceTask',
      params: {
        communityId: notification.team,
        spaceId: notification.project,
        taskId: notification.task,
      },
      query: notification.comment ? { comment: notification.comment } : undefined,
    }
  }
  return null
}

function notificationIcon(notification: NotificationRow) {
  if (notification.type === 'Rich Quote') return 'lucide-text-quote'
  return 'lucide-at-sign'
}

function notificationTargetTitle(notification: NotificationRow) {
  if (notification.poll) return pollTitles.value.get(String(notification.poll))
  if (notification.discussion) return discussionTitles.value.get(String(notification.discussion))
  if (notification.task) return taskTitles.value.get(String(notification.task))
  return null
}

function notificationLocation(notification: NotificationRow) {
  const community = notification.team ? getCommunity(notification.team)?.title : null
  const space = notification.project ? getSpace(notification.project)?.title : null
  return [community, space].filter(Boolean).join(' / ')
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

function shortTimestamp(timestamp: string) {
  let time = dayjsLocal(timestamp)
  let minutes = dayjsLocal().diff(time, 'minute')
  if (minutes < 1) return 'now'
  if (minutes < 60) return `${minutes}m`

  let hours = dayjsLocal().diff(time, 'hour')
  if (hours < 24) return `${hours}h`

  let days = dayjsLocal().diff(time, 'day')
  if (days < 7) return `${days}d`
  if (days < 365) return time.format('D MMM')
  return time.format('D MMM YY')
}

function showAvatar(notification: NotificationRow) {
  return Boolean(notification.from_user && notification.type !== 'Reaction')
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
    filters: () => ({ to_user: sessionUser.name, read }),
    fields: notificationFields,
    // `modified desc`, not `creation desc`: a reaction notification is a single row that
    // gets re-lit in place, so ordering by `creation` left a freshly raised notification
    // buried at its original position — unreachable once newer ones pushed it off the page.
    // The row still *displays* `creation`, because `modified` also moves when the row is
    // marked read and would date every read notification to the moment it was opened.
    orderBy: 'modified desc',
    // The page has no pagination control, so the window has to be wide enough to hold a
    // realistic backlog. `useList.reload()` refetches at the current offset and appends,
    // which makes a "load more" button unsafe on a list that mark-as-read reloads.
    limit: 100,
    cacheKey,
  })
}

unreadNotifications.reload()
usePageMeta(() => ({ title: 'Notifications' }))
</script>
