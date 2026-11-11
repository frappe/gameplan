import { expect } from '@playwright/test'
import { setup } from 'xstate'
import { defineFlow } from '../flow'
import type { Hold, Scene } from '../scene'

type Event =
  | { type: 'LOADS' }
  | { type: 'FAILS' }
  | { type: 'OPEN_BOOKMARK_MENU' }
  | { type: 'REMOVE_BOOKMARK' }
  | { type: 'AS_NEWCOMER' }
  | { type: 'OPEN_DRAFTS' }
  | { type: 'OPEN_DRAFT' }
  | { type: 'SELECT_DRAFT' }
  | { type: 'DELETE' }
  | { type: 'CONFIRM' }
  | { type: 'OPEN_DRAFTS_SLOWLY' }
  | { type: 'DRAFTS_FAIL' }

/**
 * Bookmarks and drafts, the two "saved for later" pages.
 *
 * `Bookmarks.vue` is `DiscussionList.vue` with `feed_type: 'bookmarks'`, so it
 * shares the feed's skeleton, empty box and "Load more" logic. It offers no way
 * to remove a bookmark: that lives in the discussion's own menu
 * (`DiscussionView.vue`).
 *
 * `Drafts.vue` reads the shared `drafts` list (`data/drafts.ts`), loaded when
 * the app boots, and picks only between "No drafts" (`data?.length === 0`)
 * and the list; selection mode is `isBulkDeleteMode` plus `selectedDrafts`.
 */
const machine = setup({ types: { events: {} as Event } }).createMachine({
  id: 'saved',
  initial: 'bookmarksSkeleton',
  states: {
    bookmarksSkeleton: {
      meta: { description: 'Bookmarks while the request is out: three skeleton rows under the header.' },
      on: { LOADS: 'bookmarks', FAILS: 'bookmarksFailed' },
    },
    bookmarksFailed: {
      meta: {
        description: 'Bookmarks after the request failed. No error and no retry: only a "Load more" button under the header.',
      },
    },
    bookmarks: {
      meta: {
        description:
          'Maya\'s five bookmarks across communities, each row showing who wrote the post, where, its opening text and its reply count.',
      },
      on: {
        OPEN_BOOKMARK_MENU: 'bookmarkMenu',
        AS_NEWCOMER: 'bookmarksEmpty',
        OPEN_DRAFTS: 'drafts',
        OPEN_DRAFTS_SLOWLY: 'draftsLoading',
      },
    },
    bookmarkMenu: {
      meta: {
        description:
          'Removing a bookmark: the Bookmarks page has no control for it, so Maya opens the post and finds "Remove Bookmark" in its options menu.',
      },
      on: { REMOVE_BOOKMARK: 'bookmarkRemoved' },
    },
    bookmarkRemoved: {
      meta: { description: 'Back on Bookmarks after removing one: four rows, with no toast or undo on either page.' },
    },
    bookmarksEmpty: {
      meta: { description: 'Felix has bookmarked nothing: the feed\'s generic "No discussions" box, with no hint about bookmarking.' },
    },
    drafts: {
      meta: { description: 'Drafts: Maya\'s one discussion draft, with its space, a text preview and when it was last edited.' },
      on: { OPEN_DRAFT: 'draftOpened', SELECT_DRAFT: 'draftSelected' },
    },
    draftOpened: {
      meta: { description: 'Opening the draft puts it back in the new-discussion composer, title and body as she left them.' },
    },
    draftSelected: {
      meta: {
        description:
          'Deleting goes through "Select drafts" in the actions menu: checkboxes appear, and with one ticked the header offers Cancel and "Delete 1 draft".',
      },
      on: { DELETE: 'confirmDelete' },
    },
    confirmDelete: {
      meta: { description: 'The confirm dialog for deleting the selected drafts: it says the delete cannot be undone and offers only Delete and the close button, no Cancel.' },
      on: { CONFIRM: 'draftsEmpty' },
    },
    draftsEmpty: {
      meta: { description: 'After the delete: a "Draft deleted" toast and the "No drafts" box.' },
    },
    draftsLoading: {
      meta: {
        description:
          'Drafts on a first visit (nothing cached) while its request is out: a blank page under the header. There is no skeleton.',
      },
      on: { DRAFTS_FAIL: 'draftsFailed' },
    },
    draftsFailed: {
      meta: {
        description:
          'Drafts after its request failed: the same blank page as loading, with no error, no retry and no "No drafts".',
      },
    },
  },
})

const holds = new WeakMap<Scene, Hold>()

const BOOKMARKS_URL = '**/api/v2/method/gameplan.gameplan.doctype.gp_discussion.api.get_discussions*'
const DRAFTS_URL = '**/api/v2/method/gameplan.gameplan.doctype.gp_draft.gp_draft.get_my_drafts*'
const DRAFT_TITLE = 'Next Fest sprint, week 1 plan (draft)'

function rows(scene: Scene) {
  return scene.page.locator('a[href*="/discussion/"]')
}

/**
 * frappe-ui keeps every list with a `cacheKey` in IndexedDB, so a reload
 * shows the drafts the boot on /bookmarks already fetched. Deleting the
 * databases from a page outside the app makes the next load a first visit.
 */
async function forgetCachedLists(scene: Scene) {
  await scene.page.goto('/api/method/ping')
  await scene.page.evaluate(async () => {
    const databases = await indexedDB.databases()
    await Promise.all(
      databases.map(
        ({ name }) =>
          new Promise<void>((resolve, reject) => {
            if (!name) return resolve()
            const request = indexedDB.deleteDatabase(name)
            request.onsuccess = () => resolve()
            request.onerror = () => reject(request.error)
          }),
      ),
    )
  })
}

function draftRow(scene: Scene) {
  return scene.page.getByText(DRAFT_TITLE)
}

export const saved = defineFlow<Event>({
  id: 'saved',
  title: 'Bookmarks and drafts',
  source:
    'frontend/src/pages/Bookmarks.vue, frontend/src/components/DiscussionList.vue, frontend/src/pages/Drafts.vue, frontend/src/data/drafts.ts',
  machine,
  async enter(scene) {
    holds.set(scene, await scene.hold(BOOKMARKS_URL))
    await scene.goto('/bookmarks')
    await expect(scene.page.getByLabel('Loading discussion').first()).toBeVisible()
  },
  events: {
    async LOADS(scene) {
      await holds.get(scene)?.release()
      await expect(rows(scene)).toHaveCount(5)
    },
    async FAILS(scene) {
      await holds.get(scene)?.abort(500)
      await expect(scene.page.getByRole('button', { name: 'Load more' })).toBeVisible({ timeout: 30_000 })
    },
    async OPEN_BOOKMARK_MENU(scene) {
      await rows(scene).first().click()
      await expect(scene.page).toHaveURL(/\/discussion\//)
      await scene.page.getByRole('button', { name: 'Discussion Options' }).click()
      await expect(scene.page.getByRole('menuitem', { name: 'Remove Bookmark' })).toBeVisible()
    },
    async REMOVE_BOOKMARK(scene) {
      await scene.page.getByRole('menuitem', { name: 'Remove Bookmark' }).click()
      await scene.page.getByRole('button', { name: 'Discussion Options' }).click()
      await expect(scene.page.getByRole('menuitem', { name: 'Bookmark', exact: true })).toBeVisible()
      await scene.page.keyboard.press('Escape')
      await scene.page.goBack()
      await expect(scene.page).toHaveURL(/\/bookmarks$/)
      await expect(rows(scene)).toHaveCount(4)
      await scene.page.mouse.move(700, 20)
    },
    async AS_NEWCOMER(scene) {
      await scene.signIn(scene.people.member)
      await scene.goto('/bookmarks')
      await expect(scene.page.getByText('No discussions')).toBeVisible()
    },
    async OPEN_DRAFTS(scene) {
      await scene.goto('/drafts')
      await expect(draftRow(scene)).toBeVisible()
    },
    async OPEN_DRAFT(scene) {
      await draftRow(scene).click()
      await expect(scene.page).toHaveURL(/draft=/)
      await expect(scene.page.getByText('First Next Fest sprint')).toBeVisible()
    },
    async SELECT_DRAFT(scene) {
      await scene.page.getByRole('button', { name: 'Draft actions' }).click()
      await scene.page.getByRole('menuitem', { name: 'Select drafts' }).click()
      await draftRow(scene).click()
      await expect(scene.page.getByRole('button', { name: 'Delete 1 draft' })).toBeVisible()
      await scene.page.mouse.move(700, 20)
    },
    async DELETE(scene) {
      await scene.page.getByRole('button', { name: 'Delete 1 draft' }).click()
      await expect(scene.page.getByRole('dialog')).toContainText('cannot be undone')
    },
    async CONFIRM(scene) {
      await scene.page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click()
      await expect(scene.page.getByText('No drafts')).toBeVisible()
      await expect(scene.page.getByText('Draft deleted')).toBeVisible()
    },
    async OPEN_DRAFTS_SLOWLY(scene) {
      await forgetCachedLists(scene)
      holds.set(scene, await scene.hold(DRAFTS_URL))
      await scene.goto('/drafts')
      await expect(scene.page.getByRole('button', { name: 'New discussion' })).toBeVisible()
      await expect(draftRow(scene)).toBeHidden()
    },
    async DRAFTS_FAIL(scene) {
      const failed = scene.page.waitForResponse((response) => response.url().includes('get_my_drafts') && response.status() === 500)
      await holds.get(scene)?.abort(500)
      await failed
      // The transport retries server errors with backoff before the list gives up.
      await scene.settle(8_000)
      await expect(draftRow(scene)).toBeHidden()
      await expect(scene.page.getByText('No drafts')).toBeHidden()
    },
  },
})
