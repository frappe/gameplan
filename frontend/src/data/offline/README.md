# data/offline

The only Gameplan code that knows how frappe-ui works inside. Everything else imports
`useList`, `useDoc` and `useCall` from `resources.ts`, and never reads or writes frappe-ui's
IndexedDB cache directly.

| File | Job | Relies on | Goes when frappe-ui has |
| --- | --- | --- | --- |
| `resources.ts` | Offline defaults: `staleOnError`, revalidation on reconnect, and `cacheLoaded` | `staleOnError` treats only non-`FrappeResponseError`s as network failures | A reconnect option, and a promise for the cached copy |
| `requests.ts` | Refuses `/api/` requests while offline, with one toast for a refused write | frappe-ui fetches through `window.fetch` | An offline check in its fetch layer |
| `cache.ts` | `cacheFor(user)`: the keys frappe-ui stores one user's lists, calls and documents under | The `useList:v2`, `useCall:v2` and `doc:v2:` key formats, under `ns:<user>:` (frappe-ui#1211) | A public cache API |

## Two accounts never mix

The session cookie can change at any moment: a sign-in in another tab, `bench browse --sid`,
the dev user switcher. So code that writes to the cache in the background must not ask who is
signed in now.

- **Bind, don't look up.** A download builds every key through `cacheFor(owner)`, fixed when it
  starts. Nothing in it reads the cookie again.
- **Answers say whose they are.** Both download endpoints return `user`, and the client drops
  any answer for another account before storing it.
- **Clearing excludes writing.** A logout or user switch stops this tab's download, then clears
  under the lock downloads hold (`DOWNLOADS_LOCK` in `offline.ts`). So no write lands after it.

`frontend/cypress/e2e/offline/downloads.cy.ts` writes through `cache.ts` and reads back
through the app's own resources, so a frappe-ui upgrade that changes the key format fails CI
rather than breaking downloads quietly.

Gameplan is pinned to the frappe-ui commit that merged frappe-ui#1211 until a release
includes it.
