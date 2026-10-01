/**
 * People who are not signed in, reading a public space.
 *
 * The server decides what they may read and cleans what it sends them
 * (gameplan/public_payload.py): authors arrive as profile handles, never emails, and there
 * are no member lists, voters or reactors. This module only decides what the app shows them.
 */

/** Whether nobody is signed in. Read from the cookie so data modules can ask at import time. */
export function isAnonymousVisitor(): boolean {
  const cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
  const user = cookies.get('user_id')
  return !user || user === 'Guest'
}

/** Whether this site lets people who are not signed in read Anonymous-tier spaces. */
export function publicAccessEnabled(): boolean {
  return Boolean(window.public_access_enabled)
}

/** Whether the current visitor is reading the public view of the app. */
export function isPublicVisitor(): boolean {
  return isAnonymousVisitor() && publicAccessEnabled()
}

/** Whether visitors may create their own account (Website Settings, "Disable signup"). */
export function signupEnabled(): boolean {
  return Boolean(window.signup_enabled)
}

function currentPath(path?: string) {
  if (path) return path
  const { pathname, search, hash } = window.location
  return pathname + search + hash
}

/** Frappe's login page, returning to `path` (or the current page) afterwards. */
export function loginUrl(path?: string): string {
  return '/login?redirect-to=' + encodeURIComponent(currentPath(path))
}

/** Frappe's own signup form, returning to `path` (or the current page) afterwards. */
export function signupUrl(path?: string): string {
  return loginUrl(path) + '#signup'
}

/**
 * The list endpoint the public view reads `doctype` from, or '' for frappe-ui's default.
 * frappe's own list route refuses anonymous visitors for Gameplan doctypes; these clean
 * every row (gameplan/public_lists.py).
 */
export function publicListUrl(
  doctype: 'GP Team' | 'GP Project' | 'GP Comment' | 'GP Poll',
): string {
  if (!isAnonymousVisitor()) return ''
  const endpoint = {
    'GP Team': 'communities',
    'GP Project': 'spaces',
    'GP Comment': 'comments',
    'GP Poll': 'polls',
  }[doctype]
  return `/api/v2/method/gameplan.public_lists.${endpoint}`
}
