/**
 * The signed-in user, from the `user_id` cookie frappe sets.
 *
 * Read from the cookie rather than from `data/session`, because the modules that need it
 * while they are loading — `data/users`, `offline` — are ones `data/session` itself imports,
 * and importing back the other way would be a cycle.
 */
export function getSessionUserFromCookie(): string | null {
  const cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
  const user = cookies.get('user_id')
  return user && user !== 'Guest' ? user : null
}
