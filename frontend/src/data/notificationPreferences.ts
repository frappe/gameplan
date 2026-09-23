import { computed, ref } from 'vue'
import { toast, useDoctype } from 'frappe-ui'
import type { GPUserProfile } from '@/types/doctypes'

export type NotificationLevel = 'Mentions only' | 'Mute'
export type NotificationChannel = 'In-app' | 'Push' | 'Email'

export type DiscussionNotificationState = 'Mute' | 'Mentions only' | 'Watch'
export type DiscussionNotificationChoice = DiscussionNotificationState | 'Default'

export const defaultNotificationLevel: NotificationLevel = 'Mentions only'

export type Weekday = 'Mon' | 'Tue' | 'Wed' | 'Thu' | 'Fri' | 'Sat' | 'Sun'
export const allWeekdays: Weekday[] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
export const allDayStart = '00:00'
export const allDayEnd = '23:59'

export const participationLevels = ['Watch', 'Mentions only'] as const
export type ParticipationLevel = (typeof participationLevels)[number]
export const defaultParticipationLevel: ParticipationLevel = 'Watch'

const level = ref<NotificationLevel>(defaultNotificationLevel)
const participation = ref<ParticipationLevel>(defaultParticipationLevel)
const receiveNotifications = ref(true)
const channel = ref<NotificationChannel>('In-app')
const activeHoursStart = ref(allDayStart)
const activeHoursEnd = ref(allDayEnd)
const activeHoursDays = ref<Weekday[]>([...allWeekdays])
const profileName = ref('')
const saving = ref(false)

const userProfiles = useDoctype<GPUserProfile>('GP User Profile')
const saveToastId = 'notification-preference-save'

export const currentNotificationLevel = computed(() => level.value)
export const currentParticipationLevel = computed(() => participation.value)
export const currentReceiveNotifications = computed(() => receiveNotifications.value)
export const currentNotificationChannel = computed(() => channel.value)
export const currentActiveHoursStart = computed(() => activeHoursStart.value)
export const currentActiveHoursEnd = computed(() => activeHoursEnd.value)
export const currentActiveHoursDays = computed(() => activeHoursDays.value)
export const isSavingNotificationPreference = computed(() => saving.value)

export function loadNotificationPreferences(
  user: {
    notification_level?: unknown
    participation_level?: unknown
    notification_channel?: unknown
    receive_notifications?: unknown
    active_hours_enabled?: unknown
    active_hours_start?: unknown
    active_hours_end?: unknown
    active_hours_days?: unknown
  },
  currentProfileName = '',
) {
  profileName.value = currentProfileName
  level.value = normalizeLevel(user.notification_level)
  participation.value = normalizeParticipation(user.participation_level)
  receiveNotifications.value = toBoolean(user.receive_notifications, true)
  channel.value = normalizeChannel(user.notification_channel)
  const scheduled = toBoolean(user.active_hours_enabled, false)
  activeHoursStart.value = (scheduled && toTime(user.active_hours_start)) || allDayStart
  activeHoursEnd.value = (scheduled && toTime(user.active_hours_end)) || allDayEnd
  activeHoursDays.value = scheduled ? normalizeDays(user.active_hours_days) : [...allWeekdays]
}

export function setNotificationLevel(value: unknown) {
  const next = normalizeLevel(value)
  const previous = level.value
  if (next === previous) return
  level.value = next
  void persist({ notification_level: next }, () => (level.value = previous))
}

export function setParticipationLevel(value: unknown) {
  const next = normalizeParticipation(value)
  const previous = participation.value
  if (next === previous) return
  participation.value = next
  void persist({ participation_level: next }, () => (participation.value = previous))
}

export function setNotificationChannel(value: unknown) {
  const next = normalizeChannel(value)
  const previous = channel.value
  if (next === previous) return
  channel.value = next
  void persist({ notification_channel: next }, () => (channel.value = previous))
}

export function setReceiveNotifications(value: boolean) {
  const previous = receiveNotifications.value
  if (value === previous) return
  receiveNotifications.value = value
  void persist(
    { receive_notifications: value ? 1 : 0 },
    () => (receiveNotifications.value = previous),
  )
}

export function setActiveHours(patch: { start?: string; end?: string; days?: Weekday[] }) {
  const previous = {
    start: activeHoursStart.value,
    end: activeHoursEnd.value,
    days: activeHoursDays.value,
  }
  const next = {
    start: patch.start || previous.start,
    end: patch.end || previous.end,
    days: patch.days ?? previous.days,
  }
  if (next.start === next.end) return
  activeHoursStart.value = next.start
  activeHoursEnd.value = next.end
  activeHoursDays.value = next.days
  const allDay =
    next.start === allDayStart && next.end === allDayEnd && next.days.length === allWeekdays.length
  void persist(
    {
      active_hours_enabled: allDay ? 0 : 1,
      active_hours_start: `${next.start}:00`,
      active_hours_end: `${next.end}:00`,
      active_hours_days: JSON.stringify(next.days),
    },
    () => {
      activeHoursStart.value = previous.start
      activeHoursEnd.value = previous.end
      activeHoursDays.value = previous.days
    },
  )
}

async function persist(patch: Partial<GPUserProfile>, rollback: () => void) {
  if (!profileName.value) return
  saving.value = true
  try {
    await userProfiles.setValue.submit({ name: profileName.value, ...patch })
    toast.success('Notification preference saved', { id: saveToastId })
  } catch {
    rollback()
    toast.error('Could not save notification preference', { id: saveToastId })
  } finally {
    saving.value = false
  }
}

function normalizeParticipation(value: unknown): ParticipationLevel {
  return participationLevels.includes(value as ParticipationLevel)
    ? (value as ParticipationLevel)
    : defaultParticipationLevel
}

function normalizeLevel(value: unknown): NotificationLevel {
  return value === 'Mute' ? 'Mute' : defaultNotificationLevel
}

function normalizeChannel(value: unknown): NotificationChannel {
  return value === 'Email' || value === 'Push' ? value : 'In-app'
}

function toBoolean(value: unknown, fallback: boolean) {
  if (value === undefined || value === null || value === '') return fallback
  return Boolean(Number(value))
}

function toTime(value: unknown) {
  if (typeof value !== 'string') return ''
  const match = value.match(/^(\d{1,2}):(\d{2})/)
  return match ? `${match[1].padStart(2, '0')}:${match[2]}` : ''
}

function normalizeDays(value: unknown): Weekday[] {
  let list: unknown = value
  if (typeof value === 'string') {
    try {
      list = JSON.parse(value)
    } catch {
      list = null
    }
  }
  if (!Array.isArray(list)) return [...allWeekdays]
  const days = allWeekdays.filter((day) => list.includes(day))
  return days.length ? days : [...allWeekdays]
}

export const discussionNotificationStates: DiscussionNotificationState[] = [
  'Mute',
  'Mentions only',
  'Watch',
]

export const discussionStateIcon: Record<DiscussionNotificationState, string> = {
  Mute: 'lucide-bell-off',
  'Mentions only': 'lucide-bell',
  Watch: 'lucide-bell-ring',
}

export const discussionStateDescription: Record<DiscussionNotificationState, string> = {
  Mute: 'Nothing from this discussion, not even mentions',
  'Mentions only': 'Only when someone @mentions you here',
  Watch: 'Every new comment, plus mentions',
}

export function discussionNotificationOptions(
  state: DiscussionNotificationState,
  onSelect: (choice: DiscussionNotificationChoice) => void,
) {
  return discussionNotificationStates.map((candidate) => ({
    label: candidate,
    description: discussionStateDescription[candidate],
    icon: discussionStateIcon[candidate],
    selected: state === candidate,
    onClick: () => onSelect(candidate),
  }))
}
