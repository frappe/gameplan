/**
 * frappe-ui's IndexedDB cache, addressed from outside its resources. frappe-ui has no public
 * API for this yet (see README.md), so the key formats below mirror its
 * `data-fetching/utils.ts` (lists) and `docStore.ts` (documents).
 */
import { keys } from 'idb-keyval'
import { getSessionUserFromCookie } from '@/utils/sessionCookie'

const VERSION = 'v2'

/** Every key frappe-ui writes for a signed-in user sits under that user. */
function namespaced(key: string) {
  const user = getSessionUserFromCookie()
  return user ? `ns:${encodeURIComponent(user)}:${key}` : key
}

/** Where `useList({ cacheKey })` keeps its rows. */
export function listKey(cacheKey: unknown[]) {
  return namespaced(JSON.stringify([`useList:${VERSION}`, ...cacheKey]))
}

/** Where `useCall({ cacheKey })` keeps its response. */
export function callKey(cacheKey: unknown[]) {
  return namespaced(JSON.stringify([`useCall:${VERSION}`, ...cacheKey]))
}

/** Where the document store keeps one document. */
export function docKey(doctype: string, name: string) {
  return namespaced(`doc:${VERSION}:${doctype}/${name}`)
}

/** The names of the documents of `doctype` cached for this user. */
export async function cachedDocNames(doctype: string) {
  const prefix = docKey(doctype, '')
  return (await keys())
    .filter((key): key is string => typeof key === 'string' && key.startsWith(prefix))
    .map((key) => key.slice(prefix.length))
}

/** The cache keys of this user's cached lists whose key begins with `first`. */
export async function cachedListKeys(first: string): Promise<unknown[][]> {
  const namespace = namespaced('')
  const prefix = listKey([first]).slice(0, -1)
  const found: unknown[][] = []
  for (const key of await keys()) {
    if (typeof key !== 'string' || !key.startsWith(prefix)) continue
    try {
      found.push(JSON.parse(key.slice(namespace.length)).slice(1))
    } catch {
      // Not a key frappe-ui wrote.
    }
  }
  return found
}
