import { createResource } from 'frappe-ui'
import { reactive } from 'vue'

let usersByName = reactive({})
export let usersResource = createResource({
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
      window.location.href = '/login'
    }
  },
})
usersResource.fetch()

export function userInfo(email) {
  if (!email) {
    email = sessionUser()
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

let _sessionUser = null
export function sessionUser() {
  if (!_sessionUser) {
    let cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
    _sessionUser = cookies.get('user_id')
  }
  return _sessionUser
}
