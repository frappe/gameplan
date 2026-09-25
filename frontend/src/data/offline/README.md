# data/offline

The only Gameplan code that knows how frappe-ui works inside. Everything else imports
`useList`, `useDoc` and `useCall` from `resources.ts`, and never reads or writes frappe-ui's
IndexedDB cache directly.

| File | Job | Relies on | Goes when frappe-ui has |
| --- | --- | --- | --- |
| `resources.ts` | Offline defaults: `staleOnError`, revalidation on reconnect, and `cacheLoaded` | `staleOnError` treats only non-`FrappeResponseError`s as network failures | A reconnect option, and a promise for the cached copy |
| `requests.ts` | Refuses `/api/` requests while offline, with one toast for a refused write | frappe-ui fetches through `window.fetch` | An offline check in its fetch layer |
| `cache.ts` | The keys frappe-ui stores lists, calls and documents under | The `useList:v2`, `useCall:v2` and `doc:v2:` key formats, under `ns:<user>:` (frappe-ui#1211) | A public cache API |

`frontend/cypress/e2e/offline/downloads.cy.ts` writes through `cache.ts` and reads back
through the app's own resources, so a frappe-ui upgrade that changes the key format fails CI
rather than breaking downloads quietly.

Gameplan is pinned to the frappe-ui commit that merged frappe-ui#1211 until a release
includes it.
