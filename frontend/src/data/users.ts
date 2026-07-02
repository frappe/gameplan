import { computed, reactive } from 'vue'
import { useCall } from 'frappe-ui'
import { setCommunityOrder } from './communityOrder'
import { loadQuickReactionSlots } from './reactionPreferences'
import { setSidebarBadgeStyle, type SidebarBadgeStyle } from './sidebarPreferences'
import { session } from './session'

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

interface UserInfo {
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
  role: 'Guest' | 'Gameplan Admin' | 'Gameplan Member' | 'Gameplan Guest'
  isGuest?: boolean
  isNotGuest?: boolean
  isDisabled?: boolean
}

export let users = useCall<UserInfo[]>({
  url: '/api/v2/method/gameplan.api.get_user_info',
  cacheKey: 'Users',
  initialData: [],
  transform(data) {
    for (let user of data) {
      user.isGuest = user.role === 'Gameplan Guest'
      user.isNotGuest = !user.isGuest
      user.isDisabled = user.enabled === 0
      usersByName[user.name] = user
      if (user.name === session.user) {
        setCommunityOrder(user.community_order)
        loadQuickReactionSlots(user.quick_reaction_emojis, user.user_profile)
        setSidebarBadgeStyle(user.sidebar_badge_style)
      }
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

export function useUser(email?: string | null) {
  if (!email || email === 'sessionUser') {
    email = session.user
  }
  if (!usersByName[email]) {
    usersByName[email] = getPlaceholderUser(email)
  }
  return usersByName[email]
}

function getPlaceholderUser(email: string) {
  const isAnonymous = email === 'Guest'
  return {
    name: email,
    email: isAnonymous ? '' : email,
    full_name: isAnonymous ? 'Guest' : email.split('@')[0],
    user_image: '',
    role: isAnonymous ? 'Guest' : 'Gameplan Member',
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

export function useSessionUser() {
  return useUser('sessionUser')
}

export function isGameplanAdmin(user: UserInfo = useSessionUser()) {
  return user.name === 'Administrator' || user.role === 'Gameplan Admin'
}
