import { computed, reactive } from 'vue'
import { useCall } from 'frappe-ui/src/data-fetching'
import router from '@/router'
import { session } from './session'

let usersByName = reactive<Record<string, UserInfo>>({})

interface UserInfo {
  name: string
  email: string
  enabled: number
  user_image: string
  full_name: string
  user_type: string
  user_profile: string
  image_background_color: string
  is_image_background_removed: number
  discussions_count_3m: number
  comments_count_3m: number
  bio: string
  role: 'Gameplan Admin' | 'Gameplan Member' | 'Gameplan Guest'
  isGuest?: boolean
  isNotGuest?: boolean
  isDisabled?: boolean
}

export let users = useCall<UserInfo[]>({
  url: '/api/v2/method/gameplan.api.get_user_info',
  cacheKey: 'Users',
  initialData: [],
  transform(users) {
    for (let user of users) {
      user.isGuest = user.role === 'Gameplan Guest'
      user.isNotGuest = !user.isGuest
      user.isDisabled = user.enabled === 0
      usersByName[user.name] = user
    }
    return users
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
  if (!email) return getPlaceholderUser('guest@example.com', 'Guest')
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

export function useSessionUser() {
  return useUser('sessionUser')
}
