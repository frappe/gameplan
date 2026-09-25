/**
 * frappe-ui's IndexedDB cache, addressed from outside its resources. frappe-ui has no public
 * API for this yet (see README.md), so the key formats below mirror its
 * `data-fetching/utils.ts` (lists and calls) and `docStore.ts` (documents).
 */
import { keys } from 'idb-keyval'
import { getSessionUserFromCookie } from '@/utils/sessionCookie'

const VERSION = 'v2'

/**
 * The keys frappe-ui files `user`'s cache under; by default the signed-in user's. A sync binds
 * them to the account it started as, so a sign-in in another tab cannot redirect its writes.
 */
export function cacheFor(user = getSessionUserFromCookie()) {
  const namespace = user ? `ns:${encodeURIComponent(user)}:` : ''
  const listKey = (cacheKey: unknown[]) =>
    namespace + JSON.stringify([`useList:${VERSION}`, ...cacheKey])
  const docKey = (doctype: string, name: string) => `${namespace}doc:${VERSION}:${doctype}/${name}`

  return {
    /** Where `useList({ cacheKey })` keeps its rows. */
    listKey,
    /** Where `useCall({ cacheKey })` keeps its response. */
    callKey: (cacheKey: unknown[]) =>
      namespace + JSON.stringify([`useCall:${VERSION}`, ...cacheKey]),
    /** Where the document store keeps one document. */
    docKey,

    /** The names of the cached documents of `doctype`. */
    async docNames(doctype: string) {
      const prefix = docKey(doctype, '')
      return (await keys())
        .filter((key): key is string => typeof key === 'string' && key.startsWith(prefix))
        .map((key) => key.slice(prefix.length))
    },

    /** The cache keys of the cached lists whose key begins with `first`. */
    async listKeys(first: string): Promise<unknown[][]> {
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
    },
  }
}

export type Cache = ReturnType<typeof cacheFor>
