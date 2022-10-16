import { createResource } from 'frappe-ui'
import { reactive } from 'vue'
import router from '@/router'
import { session } from './session'

let usersByName = reactive({})
export let users = createResource({
  method: 'gameplan.api.get_user_info',
  cache: 'Users',
  initialData: [],
  onData(users) {
    for (let user of users) {
      usersByName[user.name] = user
    }
  },
  onError(error) {
    if (error && error.exc_type === 'AuthenticationError') {
      router.push('/login')
    }
  },
})
users.reload = () => {
  users.promise = users.fetch()
  return users.promise
}

users.reload()

export function userInfo(email) {
  if (!email) {
    email = session.user
  }
  if (!usersByName[email]) {
    usersByName[email] = {
      name: email,
      email: email,
      full_name: email.split('@')[0],
      user_image: null,
    }
  }
  return usersByName[email]
}
