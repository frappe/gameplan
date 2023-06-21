import { createResource } from 'frappe-ui'
import { computed, reactive } from 'vue'
import router from '@/router'
import { session } from './session'

let usersByName = reactive({})
export let users = createResource({
  url: 'gameplan.api.get_user_info',
  cache: 'Users',
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
    if (error && error.exc_type === 'AuthenticationError') {
      router.push('/login')
    }
  },
})

export function getUser(email) {
  if (!email || email === 'sessionUser') {
    email = session.user
  }
  if (!usersByName[email]) {
    usersByName[email] = {
      name: email,
      email: email,
      full_name: email.split('@')[0],
      user_image: null,
      role: null,
    }
  }
  return usersByName[email]
}

export let activeUsers = computed(() => {
  return users.data.filter((user) => user.enabled)
})
