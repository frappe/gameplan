import { computed, reactive } from 'vue'
import { useCall } from 'frappe-ui'
import router from '@/router'
import { setCommunityOrder } from './communityOrder'
import { loadQuickReactionSlots } from './reactionPreferences'
import { setSidebarBadgeStyle, type SidebarBadgeStyle } from './sidebarPreferences'
import { session } from './session'
import { onSocketEvent } from '@/socket'

export type EmailDigestFrequency = 'Off' | 'Weekly' | 'Fortnightly' | 'Monthly'
export type EmailDigestDayOfWeek =
  | 'Monday'
  | 'Tuesday'
  | 'Wednesday'
  | 'Thursday'
  | 'Friday'
  | 'Saturday'
  | 'Sunday'

let usersByName = reactive<Record<string, UserInfo>>({})

export interface UserInfo {
  name: string
  email: string
  enabled: number
  user_image: string
  full_name: string
  user_type: string
  creation: string
  user_profile: string
  image_background_color: string
  is_image_background_removed: number
  discussions_count_3m: number
  comments_count_3m: number
  community_order?: unknown
  quick_reaction_emojis?: unknown
  sidebar_badge_style?: SidebarBadgeStyle
  email_digest_frequency?: EmailDigestFrequency
  email_digest_day_of_week?: EmailDigestDayOfWeek
  email_digest_last_sent_on?: string
  bio: string
  role: 'Gameplan Admin' | 'Gameplan Member' | 'Gameplan Guest'
  isGuest?: boolean
  isNotGuest?: boolean
  isDisabled?: boolean
  /**
   * True for a record `useUser` invented because the id is not in the store — either the
   * user list has not loaded yet, or the user is not in it at all (`get_user_info` only
   * returns users holding a Gameplan role). Its `full_name` is a guess (the local part of
   * the email), so callers with a better name of their own should prefer theirs.
   */
  isPlaceholder?: boolean
}

function mergeUserInfo(user: UserInfo) {
  user.isGuest = user.role === 'Gameplan Guest'
  user.isNotGuest = !user.isGuest
  user.isDisabled = user.enabled === 0
  // Set explicitly (not just left undefined) so merging a real record over a placeholder
  // already in the store clears the flag — `Object.assign` only copies keys it has.
  user.isPlaceholder = false
  const existing = usersByName[user.name]
  if (existing) {
    Object.assign(existing, user)
  } else {
    usersByName[user.name] = user
  }
  if (user.name === session.user) {
    setCommunityOrder(user.community_order)
    loadQuickReactionSlots(user.quick_reaction_emojis, user.user_profile)
    setSidebarBadgeStyle(user.sidebar_badge_style)
  }
}

export let users = useCall<UserInfo[]>({
  url: '/api/v2/method/gameplan.api.get_user_info',
  cacheKey: 'Users',
  initialData: [],
  transform(data) {
    for (let user of data) {
      mergeUserInfo(user)
    }
    return data
  },
  onError(error) {
    if (error && error.type === 'AuthenticationError') {
      window.location.href = '/login'
    }
  },
  immediate: false,
})

// A profile edit changes what everyone else renders (avatar, name, role), so the backend
// broadcasts this to every session. Skipped until the list has actually loaded: `users` is
// `immediate: false` and App.vue fetches it once the session is known, and reloading before
// that would race that first fetch on the same instance.
onSocketEvent('gameplan:users_changed', () => {
  if (users.data) users.reload()
})

export function updateUserInfo(user: UserInfo) {
  mergeUserInfo(user)
  const listedUser = users.data?.find((item) => item.name === user.name)
  if (listedUser) Object.assign(listedUser, user)
}

// Shared so `useUser('')` is referentially stable across renders, and never lands in
// `usersByName` (its key would be the empty string and the next unknown actor would
// inherit whatever the last one merged into it).
const unknownUser = getPlaceholderUser('', 'Unknown')

/**
 * Resolve a user id to its `UserInfo`, or to a placeholder (`isPlaceholder`) when the id
 * is not in the store — the user list is still loading, or the user is not in it at all.
 *
 * "The session user" is what *calling it with no arguments* means, plus the explicit
 * `'sessionUser'` sentinel. Any id that is actually passed resolves to that id, and an
 * empty, `null` or `undefined` one resolves to the shared Unknown placeholder — never to
 * the session user. That is why the sentinel is an arity check and not a parameter
 * default: a default also fires for an explicitly passed `undefined`, which is how the
 * viewer's own name ended up rendered as the actor on someone else's activity whenever
 * the actor field came back empty.
 */
export function useUser(...args: [] | [email: string | null | undefined]): UserInfo {
  let email = args.length === 0 ? session.user : args[0]
  if (email === 'sessionUser') {
    email = session.user
  }
  if (!email) return unknownUser
  if (!usersByName[email]) {
    usersByName[email] = getPlaceholderUser(email, email.split('@')[0])
  }
  return usersByName[email]
}

function getPlaceholderUser(email: string, full_name: string) {
  return {
    name: email,
    email: email,
    full_name: full_name,
    isPlaceholder: true,
    user_image: '',
    role: 'Gameplan Member',
    enabled: 1,
    user_profile: '',
    image_background_color: '',
    is_image_background_removed: 0,
    user_type: 'Website User',
  } as UserInfo
}

export let activeUsers = computed(() => {
  return (users.data || []).filter((user) => user.enabled)
})

/**
 * How many people the People page lists: enabled accounts, guests excluded.
 *
 * Derived from the already-loaded user list rather than a count query, so the rail can
 * show it without a request of its own.
 */
export const memberCount = computed(() => {
  return activeUsers.value.filter((user) => user.isNotGuest).length
})

export function useSessionUser() {
  return useUser('sessionUser')
}

export function isGameplanAdmin(user: UserInfo = useSessionUser()) {
  return user.name === 'Administrator' || user.role === 'Gameplan Admin'
}
