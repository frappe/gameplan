# data/offline

These adapters isolate frappe-ui's cache contract. Components import `useList`, `useDoc`,
`useCall` and `dialog` through the `resources.ts` alias. Bulk downloads use `cacheFor(owner)`
to populate the same account-scoped entries, including thread-reaction call responses.

## Offline actions

No button is disabled for being offline. An action that needs the server says so with one
toast, "You're offline. Reconnect to do this.", at the first step: a button calls
`refuseOffline()`, and a confirm dialog is refused before it opens. What works on this device
goes ahead: discarding an edit, removing downloads. Typed text is kept as a draft. Fields that
save as you type (task, page, profile) are read-only instead, since typing there would be lost.

| File           | Job                                                                                                                                   | Relies on                                                                                                   | Goes when frappe-ui has                                                |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `resources.ts` | Offline defaults: `staleOnError`, revalidation on reconnect, `cacheLoaded`, and `dialog` refused offline                              | `staleOnError` treats only non-`FrappeResponseError`s as network failures; `dialog` methods take `onCancel` | A reconnect option, promise for cached copy, and offline dialog option |
| `requests.ts`  | Refuses `/api/` requests while offline, with one toast for a write the person asked for; `refuseOffline()` for actions to check first | frappe-ui fetches through `window.fetch`                                                                    | An offline check in its fetch layer                                    |
| `cache.ts`     | `cacheFor(user)`: the keys frappe-ui stores one user's lists, calls and documents under                                               | The `useList:v2`, `useCall:v2` and `doc:v2:` key formats, under `ns:<user>:` (frappe-ui#1211)               | A public cache API                                                     |

## Two accounts never mix

The session cookie can change at any moment: a sign-in in another tab, `bench browse --sid`,
the dev user switcher. So code that writes to the cache in the background must not ask who is
signed in now.

- **Bind, don't look up.** A download builds every key through `cacheFor(owner)`, fixed when it
  starts. Nothing in it reads the cookie again.
- **Answers say whose they are.** Both download endpoints return `user`, and the client drops
  any answer for another account before storing it.
- **Clearing excludes writing.** A logout or user switch stops this tab's download, then clears
  under the lock downloads hold (`DOWNLOADS_LOCK` in `offline.ts`). The worker advances a
  persistent cache generation before clearing images and the shell. Its writes check that
  generation under the same lock as its clear, so a response from before the clear cannot land
  after it. Image batches carry the generation from before their download started.

Cleanup upgrades a worker that cannot acknowledge the clear before the app mounts.
The replacement must take control and acknowledge cleanup before an account switch succeeds.
If the upgrade or cleanup fails, the previous-user marker stays and the app remains blocked.
Media buckets have a separate guarded namespace, so late legacy writes are never read.
Each sync retries images from the discussions already stored on the device, without refetching unchanged bundles.

Downloaded discussions are checked for lost access on every sync. The remaining visited
discussions rotate through the rest of the index's 2,000-ID budget. Leaving the download window
alone does not remove a discussion the user can still read.

`frontend/cypress/e2e/offline/downloads.cy.ts` writes through `cache.ts` and reads back
through the app's own resources, so a frappe-ui upgrade that changes the key format fails CI
rather than breaking downloads quietly.

Gameplan pins frappe-ui 1.0.2, which includes the account-scoped cache contract from
frappe-ui#1211.

Connectivity and draft save helpers live in `../online.ts`, introduced with draft synchronization.
