import { createResource } from 'frappe-ui'

let usersByName = {}
export let usersResource = createResource({
  method: 'gameplan.api.get_user_info',
  cache: 'users',
  initialData: [],
  onSuccess(users) {
    for (let user of users) {
      usersByName[user.name] = user
    }
  },
})
usersResource.fetch()

export function userInfo(email) {
  if (!email) {
    email = sessionUser()
  }
  let fallback = {
    name: email,
    email: email,
    full_name: email.split('@')[0],
    user_image: null,
  }
  return usersByName[email] || fallback
}

let _sessionUser = null
export function sessionUser() {
  if (!_sessionUser) {
    let cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
    _sessionUser = cookies.get('user_id')
  }
  return _sessionUser
}
