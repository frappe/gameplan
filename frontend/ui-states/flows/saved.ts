import { expect } from '@playwright/test'
import { setup } from 'xstate'
import { defineFlow, pressEmpty } from '../flow'
import type { Hold, Scene } from '../scene'

type Event =
  | { type: 'LOADS' }
  | { type: 'FAILS' }
  | { type: 'OPEN_BOOKMARK_MENU' }
  | { type: 'REMOVE_BOOKMARK' }
  | { type: 'HOVER_BOOKMARK' }
  | { type: 'REMOVE_FROM_LIST' }
  | { type: 'AS_NEWCOMER' }
  | { type: 'OPEN_DRAFTS' }
  | { type: 'OPEN_DRAFT' }
  | { type: 'BACK_TO_DRAFTS' }
  | { type: 'SELECT_DRAFT' }
  | { type: 'DELETE' }
  | { type: 'CONFIRM' }
  | { type: 'OPEN_DRAFTS_SLOWLY' }
  | { type: 'DRAFTS_FAIL' }

/**
 * Bookmarks and drafts, the two "saved for later" pages.
 *
 * `Bookmarks.vue` is `DiscussionList.vue` with `feed_type: 'bookmarks'` and
 * `removable-bookmarks`, so it shares the feed's skeleton, `LoadError` and
 * empty box, and each row has a hover "Remove bookmark" button
 * (`DiscussionRow.vue`) whose toast offers Undo. The discussion's own menu
 * (`DiscussionView.vue`) can remove a bookmark too.
 *
 * `Drafts.vue` reads the shared `drafts` list (`data/drafts.ts`), loaded when
 * the app boots and reloaded each time the page opens, and its `phase` picks skeleton rows, `LoadError`, "No drafts"
 * or the list; selection mode is `isBulkDeleteMode` plus `selectedDrafts`.
 */
const machine = setup({ types: { events: {} as Event } }).createMachine({
  id: 'saved',
  initial: 'bookmarksSkeleton',
  states: {
    bookmarksSkeleton: {
      meta: {
        description: 'Bookmarks while the request is out: three skeleton rows under the header.',
      },
      on: { LOADS: 'bookmarks', FAILS: 'bookmarksFailed' },
    },
    bookmarksFailed: {
      meta: {
        description:
          'Bookmarks after the request failed: "Could not load discussions." and a Retry button where the rows would be.',
      },
    },
    bookmarks: {
      meta: {
        description:
          "Maya's five bookmarks across communities, each row showing who wrote the post, where, its opening text and its reply count.",
      },
      on: {
        OPEN_BOOKMARK_MENU: 'bookmarkMenu',
        HOVER_BOOKMARK: 'bookmarkHover',
        AS_NEWCOMER: 'bookmarksEmpty',
        OPEN_DRAFTS: 'drafts',
        OPEN_DRAFTS_SLOWLY: 'draftsLoading',
      },
    },
    bookmarkMenu: {
      meta: {
        description:
          'The other way to remove a bookmark: Maya opens the post, and its "Discussion options" menu has "Remove bookmark".',
      },
      on: { REMOVE_BOOKMARK: 'bookmarkRemoved' },
    },
    bookmarkRemoved: {
      meta: {
        description:
          "Back on Bookmarks after removing one from the post's menu: four rows, and no toast on either page.",
      },
    },
    bookmarkHover: {
      meta: {
        description:
          'The pointer on the first bookmark row\'s remove button, with its "Remove bookmark" tooltip. The row is highlighted and the button takes the place of the date and reply count at its right edge.',
      },
      on: { REMOVE_FROM_LIST: 'bookmarkRemovedToast' },
    },
    bookmarkRemovedToast: {
      meta: {
        description:
          'After clicking the row\'s remove button: the row is gone, four bookmarks are left, and a "Bookmark removed" toast offers Undo.',
      },
    },
    bookmarksEmpty: {
      meta: {
        description:
          'Felix has bookmarked nothing: a bookmark icon, "No bookmarks" and "Bookmark a discussion from its ••• menu to find it here."',
      },
    },
    drafts: {
      meta: {
        description:
          'Drafts: Maya\'s one discussion draft, with her avatar, a second line that starts with "Community / Space:" before a text preview, and when it was last edited.',
      },
      on: { OPEN_DRAFT: 'draftOpened', SELECT_DRAFT: 'draftSelected' },
    },
    draftOpened: {
      meta: {
        description:
          'Opening the draft puts it back in the new-discussion composer, title and body as she left them.',
      },
      on: { BACK_TO_DRAFTS: 'draftLeft' },
    },
    draftLeft: {
      meta: {
        description:
          'Back on Drafts after leaving the composer: the draft Maya just left still has its "Community / Space:" prefix, because Drafts reloads the list when it opens.',
      },
    },
    draftSelected: {
      meta: {
        description:
          'Deleting goes through "Select drafts" in the "Draft actions" menu: checkboxes appear, and with one ticked the header offers Cancel and a red "Delete 1 draft".',
      },
      on: { DELETE: 'confirmDelete' },
    },
    confirmDelete: {
      meta: {
        description:
          'The confirm before deleting: "Delete 1 draft?", "The draft will be deleted. This can\'t be undone.", with Cancel and a red Delete. No icon in the title.',
      },
      on: { CONFIRM: 'draftsEmpty' },
    },
    draftsEmpty: {
      meta: {
        description:
          'After the delete: a "Draft deleted" toast, and a full-width box with an icon, "No drafts" and "Discussions you start and don\'t publish are saved here."',
      },
    },
    draftsLoading: {
      meta: {
        description:
          'Drafts on a first visit (nothing cached) while its request is out: three skeleton rows under the header.',
      },
      on: { DRAFTS_FAIL: 'draftsFailed' },
    },
    draftsFailed: {
      meta: {
        description:
          'Drafts after its request failed: a full-width box with a cloud icon, "Could not load your drafts." and a Retry button where the rows would be.',
      },
    },
  },
})

const holds = new WeakMap<Scene, Hold>()

const BOOKMARKS_URL =
  '**/api/v2/method/gameplan.gameplan.doctype.gp_discussion.api.get_discussions*'
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
      await expect(scene.page.getByText('Could not load discussions.')).toBeVisible({
        timeout: 30_000,
      })
      await expect(scene.page.getByRole('button', { name: 'Retry' })).toBeVisible()
    },
    async OPEN_BOOKMARK_MENU(scene) {
      await rows(scene).first().click()
      await expect(scene.page).toHaveURL(/\/discussion\//)
      await pressEmpty(scene.page)
      await scene.page.getByRole('button', { name: 'Discussion options' }).click()
      await expect(scene.page.getByRole('menuitem', { name: 'Remove bookmark' })).toBeVisible()
    },
    async REMOVE_BOOKMARK(scene) {
      await scene.page.getByRole('menuitem', { name: 'Remove bookmark' }).click()
      await scene.page.getByRole('button', { name: 'Discussion options' }).click()
      await expect(
        scene.page.getByRole('menuitem', { name: 'Bookmark', exact: true }),
      ).toBeVisible()
      await scene.page.keyboard.press('Escape')
      await scene.page.goBack()
      await expect(scene.page).toHaveURL(/\/bookmarks$/)
      await expect(rows(scene)).toHaveCount(4)
      await scene.page.mouse.move(700, 20)
    },
    async HOVER_BOOKMARK(scene) {
      const row = rows(scene).first()
      await row.hover()
      const remove = row.getByRole('button', { name: 'Remove bookmark' })
      await expect(remove).toBeVisible()
      await remove.hover()
      // frappe-ui opens a tooltip after a short delay.
      await scene.settle(1_000)
    },
    async REMOVE_FROM_LIST(scene) {
      await rows(scene).first().getByRole('button', { name: 'Remove bookmark' }).click()
      await expect(rows(scene)).toHaveCount(4)
      await expect(scene.page.getByText('Bookmark removed')).toBeVisible()
      await expect(scene.page.getByRole('button', { name: 'Undo' })).toBeVisible()
      await scene.page.mouse.move(700, 20)
    },
    async AS_NEWCOMER(scene) {
      await scene.signIn(scene.people.member)
      await scene.goto('/bookmarks')
      await expect(scene.page.getByText('No bookmarks')).toBeVisible()
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
    async BACK_TO_DRAFTS(scene) {
      const reloaded = scene.page.waitForResponse(
        (response) => response.url().includes('get_my_drafts') && response.ok(),
      )
      await scene.page.goBack()
      await expect(scene.page).toHaveURL(/\/drafts$/)
      await reloaded
      await expect(draftRow(scene)).toBeVisible()
      await expect(scene.page.locator('.body-container').getByText(/ \/ .*:/)).toBeVisible()
      await scene.page.mouse.move(700, 20)
    },
    async SELECT_DRAFT(scene) {
      await pressEmpty(scene.page)
      await scene.page.getByRole('button', { name: 'Draft actions' }).click()
      await scene.page.getByRole('menuitem', { name: 'Select drafts' }).click()
      await draftRow(scene).click()
      await expect(scene.page.getByRole('button', { name: 'Delete 1 draft' })).toBeVisible()
      await scene.page.mouse.move(700, 20)
    },
    async DELETE(scene) {
      await scene.page.getByRole('button', { name: 'Delete 1 draft' }).click()
      await expect(scene.page.getByRole('dialog')).toContainText('Delete 1 draft?')
      await expect(
        scene.page.getByRole('dialog').getByRole('button', { name: 'Cancel' }),
      ).toBeVisible()
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
      await expect(scene.page.getByLabel('Loading draft').first()).toBeVisible()
    },
    async DRAFTS_FAIL(scene) {
      const failed = scene.page.waitForResponse(
        (response) => response.url().includes('get_my_drafts') && response.status() === 500,
      )
      await holds.get(scene)?.abort(500)
      await failed
      // The transport retries server errors with backoff before the list gives up.
      await expect(scene.page.getByText('Could not load your drafts.')).toBeVisible({
        timeout: 30_000,
      })
      await expect(scene.page.getByRole('button', { name: 'Retry' })).toBeVisible()
    },
  },
})
