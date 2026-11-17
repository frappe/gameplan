/**
 * The signed-in user as Frappe's `user_id` cookie names it, or `null` for a guest.
 *
 * The cookie is set before the app boots, so this works before any request returns.
 * Keep this file free of imports: session and preference modules read it while they
 * load, and an import here could close a cycle between them.
 */
export function sessionUserFromCookie(): string | null {
  const user = new URLSearchParams(document.cookie.split('; ').join('&')).get('user_id')
  return user === 'Guest' ? null : user
}
