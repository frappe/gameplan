import { expect } from '@playwright/test'
import { setup } from 'xstate'
import { defineFlow, pressEmpty } from '../flow'
import { communities, type Hold, type Scene } from '../scene'

type Event =
  | { type: 'LOADS' }
  | { type: 'FAILS' }
  | { type: 'OPEN_MENU' }
  | { type: 'SHOW_UNREAD' }
  | { type: 'MARK_ALL_READ' }
  | { type: 'CONFIRM_READ' }
  | { type: 'MOVE_DISCUSSIONS' }
  | { type: 'ARCHIVE' }
  | { type: 'CONFIRM_ARCHIVE' }
  | { type: 'OPEN_EMPTY_SPACE' }
  | { type: 'OPEN_MISSING_SPACE' }
  | { type: 'SPACES_FAIL' }

/**
 * A space's discussion list, its "Space actions" menu and what each action
 * leads to. `Space.vue` renders the child page only once the space is in the
 * global spaces list; otherwise `SpaceUnavailable.vue` shows "Space not found"
 * once that list has loaded without it, or `LoadError` with Retry if the list
 * failed. `SpaceDiscussions.vue` holds the feed tabs (`DiscussionFeedBar.vue`, with
 * the tab in the path, `/discussions/unread`), the menu, the bulk-move mode and the dialogs;
 * `DiscussionList.vue` picks skeleton rows, rows, `LoadError` or the empty box.
 * The confirms and the archive toast live in `data/spaces.ts`.
 */
const machine = setup({ types: { events: {} as Event } }).createMachine({
  id: 'space',
  initial: 'skeleton',
  states: {
    skeleton: {
      meta: {
        description:
          'QA & Playtests while its discussion list is still loading: the header, the All discussions / Participating / Unread tabs and the sort are drawn, with three skeleton rows below.',
      },
      on: { LOADS: 'populated', FAILS: 'failed' },
    },
    failed: {
      meta: {
        description:
          'The discussion list request failed: "Could not load discussions." and a Retry button under the tabs, where the rows would be.',
      },
    },
    populated: {
      meta: {
        description:
          'QA & Playtests on the All discussions tab: the same tab bar and sort as the community feed, no Pages or Tasks tabs, and a solid "New discussion" button. The smoke-test thread Maya has not opened is in bold, with its unread count in an orange badge.',
      },
      on: {
        OPEN_MENU: 'spaceMenu',
        SHOW_UNREAD: 'unreadTab',
        MOVE_DISCUSSIONS: 'bulkMove',
        OPEN_EMPTY_SPACE: 'empty',
        OPEN_MISSING_SPACE: 'notFound',
        SPACES_FAIL: 'spacesFailed',
      },
    },
    spaceMenu: {
      meta: {
        description:
          'The "Space actions" menu for an admin, in three groups: Pin space, Copy link, "Mark all as read…"; "Settings…", "Manage access…", Move discussions; then "Archive…". No Join or Leave space.',
      },
      on: { MARK_ALL_READ: 'markAllReadConfirm', ARCHIVE: 'archiveConfirm' },
    },
    unreadTab: {
      meta: {
        description:
          "The Unread tab of QA & Playtests (`/discussions/unread`): only the smoke-test thread Maya has not opened, with the space's unread count after the tab label.",
      },
    },
    markAllReadConfirm: {
      meta: {
        description:
          'The confirm before marking the space read: "Mark all discussions in QA & Playtests as read?", one sentence on the effect, Cancel and "Mark all as read". No icon, not red.',
      },
      on: { CONFIRM_READ: 'allRead' },
    },
    allRead: {
      meta: {
        description:
          'After Mark all as read: the sidebar count beside QA & Playtests and the Unread tab count clear, but the list is not refetched, so the smoke-test row is still bold with its orange 6.',
      },
    },
    bulkMove: {
      meta: {
        description:
          'Move discussions mode: each row has a checkbox, the header offers Cancel and a disabled "Move discussions" until something is picked.',
      },
    },
    archiveConfirm: {
      meta: {
        description:
          'The confirm before archiving: "Archive QA & Playtests?", saying the space becomes read-only and leaves the feeds, with Cancel and "Archive". No icon, not red.',
      },
      on: { CONFIRM_ARCHIVE: 'archived' },
    },
    archived: {
      meta: {
        description:
          'The archived space: an "Archived" badge before the ••• menu, no "New discussion" button, a "Space archived" toast with Undo, and QA & Playtests dimmed in the sidebar but still in its place.',
      },
    },
    empty: {
      meta: {
        description:
          'A new space with no discussions yet: an icon, "No discussions yet" and "New discussions will show up here." under the tabs.',
      },
    },
    notFound: {
      meta: {
        description:
          'A space id that does not exist: "Space not found" in place, inside the community\'s sidebar, with "Go to Home", under a header that reads "Common Room / Not found".',
      },
    },
    spacesFailed: {
      meta: {
        description:
          'The global spaces list failed to load: under a "Common Room" header the page shows a cloud icon, "Could not load spaces." and Retry, and the sidebar says "Could not load spaces." with its own Retry button. No "Space not found".',
      },
    },
  },
})

const holds = new WeakMap<Scene, Hold>()
const spaceIds = new WeakMap<Scene, string>()

const LIST_URL = '**/api/v2/method/gameplan.gameplan.doctype.gp_discussion.api.get_discussions*'
const SPACES_LIST_URL = /\/api\/v2\/document\/GP(%20|\+| )Project\?/
const COMMUNITY = communities.commonRoom
const SPACE_TITLE = 'QA & Playtests'

function rows(scene: Scene) {
  return scene.page.locator('a[href*="/discussion/"]')
}

async function openMenu(scene: Scene) {
  await pressEmpty(scene.page)
  await scene.page.getByRole('button', { name: 'Space actions' }).click()
  await expect(scene.page.getByRole('menuitem', { name: 'Copy link' })).toBeVisible()
}

async function pick(scene: Scene, label: string) {
  await scene.page.getByRole('menuitem', { name: label }).click()
}

function dialog(scene: Scene) {
  return scene.page.getByRole('dialog')
}

async function openSpace(scene: Scene, space: string) {
  await scene.goto(`/community/${COMMUNITY}/space/${space}/discussions`)
}

export const space = defineFlow<Event>({
  id: 'space',
  title: 'Space page',
  folderTitle: 'Level Editor Feedback',
  source:
    'frontend/src/pages/Space.vue, frontend/src/pages/SpaceDiscussions.vue, frontend/src/components/DiscussionList.vue, frontend/src/data/spaces.ts',
  machine,
  async enter(scene) {
    const id = await scene.find('GP Project', { title: SPACE_TITLE })
    spaceIds.set(scene, id)
    holds.set(scene, await scene.hold(LIST_URL))
    await openSpace(scene, id)
    await expect(scene.page.getByLabel('Loading discussion').first()).toBeVisible()
  },
  events: {
    async LOADS(scene) {
      await holds.get(scene)?.release()
      await expect(rows(scene).nth(5)).toBeVisible()
    },
    async FAILS(scene) {
      await holds.get(scene)?.abort(500)
      await expect(scene.page.getByText('Could not load discussions.')).toBeVisible({
        timeout: 30_000,
      })
      await expect(scene.page.getByRole('button', { name: 'Retry' })).toBeVisible()
    },
    async OPEN_MENU(scene) {
      await openMenu(scene)
      await expect(scene.page.getByRole('menuitem', { name: 'Archive…' })).toBeVisible()
      await expect(
        scene.page.getByRole('menuitem', { name: /Join space|Leave space/ }),
      ).toHaveCount(0)
    },
    async SHOW_UNREAD(scene) {
      await scene.page.getByRole('radio', { name: /^Unread/ }).click()
      await expect(scene.page).toHaveURL(/\/discussions\/unread$/)
      await expect(rows(scene).first()).toBeVisible()
      await expect(rows(scene).nth(1)).toBeHidden()
      await scene.page.mouse.move(700, 20)
    },
    async MARK_ALL_READ(scene) {
      await pick(scene, 'Mark all as read…')
      await expect(
        dialog(scene).getByText(`Mark all discussions in ${SPACE_TITLE} as read?`),
      ).toBeVisible()
    },
    async CONFIRM_READ(scene) {
      const marked = scene.page.waitForResponse((r) => r.url().includes('mark_all_as_read'))
      await dialog(scene).getByRole('button', { name: 'Mark all as read' }).click()
      await marked
      await expect(dialog(scene)).toBeHidden()
      // The sidebar count is the one thing that refreshes; the list keeps its bold row.
      await scene.page.waitForLoadState('networkidle')
    },
    async MOVE_DISCUSSIONS(scene) {
      await openMenu(scene)
      await pick(scene, 'Move discussions')
      await expect(scene.page.getByRole('button', { name: 'Cancel' })).toBeVisible()
      await expect(scene.page.getByRole('checkbox').first()).toBeVisible()
      await scene.page.mouse.move(700, 20)
    },
    async ARCHIVE(scene) {
      await pick(scene, 'Archive…')
      await expect(dialog(scene).getByText(`Archive ${SPACE_TITLE}?`)).toBeVisible()
    },
    async CONFIRM_ARCHIVE(scene) {
      await dialog(scene).getByRole('button', { name: 'Archive' }).click()
      await expect(dialog(scene)).toBeHidden()
      await expect(scene.page.getByText('Archived', { exact: true })).toBeVisible()
      await expect(scene.page.getByRole('button', { name: 'New discussion' })).toBeHidden()
      await expect(scene.page.getByText('Space archived')).toBeVisible()
      await expect(scene.page.getByRole('button', { name: 'Undo' })).toBeVisible()
    },
    async OPEN_EMPTY_SPACE(scene) {
      const empty = await scene.space(COMMUNITY)
      // A full navigation, so the spaces list is fetched again and includes the new space.
      await openSpace(scene, empty.name)
      await expect(scene.page.getByText('No discussions yet')).toBeVisible()
    },
    async OPEN_MISSING_SPACE(scene) {
      await openSpace(scene, '99999')
      await expect(scene.page.getByText('Space not found', { exact: true })).toBeVisible()
      await expect(scene.page.getByText('Not found', { exact: true })).toBeVisible()
    },
    async SPACES_FAIL(scene) {
      const spacesList = await scene.hold(SPACES_LIST_URL)
      await spacesList.abort(500)
      await openSpace(scene, spaceIds.get(scene) as string)
      await expect(scene.page.getByRole('button', { name: 'Retry' })).toHaveCount(2, {
        timeout: 30_000,
      })
      await expect(scene.page.getByText('Space not found')).toHaveCount(0)
    },
  },
})
