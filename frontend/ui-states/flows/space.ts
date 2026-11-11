import { expect } from '@playwright/test'
import { setup } from 'xstate'
import { defineFlow } from '../flow'
import { communities, type Hold, type Scene } from '../scene'

type Event =
  | { type: 'LOADS' }
  | { type: 'FAILS' }
  | { type: 'OPEN_MENU' }
  | { type: 'JOIN' }
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
 * global spaces list, and "Page not found" once that list has finished without
 * it. `SpaceDiscussions.vue` holds the menu, the bulk-move mode and the dialogs;
 * `DiscussionList.vue` picks skeleton rows, rows or "No discussions".
 */
const machine = setup({ types: { events: {} as Event } }).createMachine({
  id: 'space',
  initial: 'skeleton',
  states: {
    skeleton: {
      meta: {
        description:
          'QA & Playtests while its discussion list is still loading: the header, tabs and sort are drawn, with three skeleton rows below.',
      },
      on: { LOADS: 'populated', FAILS: 'failed' },
    },
    failed: {
      meta: {
        description:
          'The discussion list request failed. No error message and no rows: only a "Load more" button under the tabs.',
      },
    },
    populated: {
      meta: {
        description:
          'QA & Playtests: every discussion, newest activity first. The smoke-test thread Maya has not opened is in bold, with its unread count in an orange badge.',
      },
      on: {
        OPEN_MENU: 'spaceMenu',
        MOVE_DISCUSSIONS: 'bulkMove',
        OPEN_EMPTY_SPACE: 'empty',
        OPEN_MISSING_SPACE: 'notFound',
        SPACES_FAIL: 'spacesFailed',
      },
    },
    spaceMenu: {
      meta: {
        description:
          'The "Space actions" menu for an admin who has not joined the space: Pin, Settings, Copy link, Mark all as read, Join space, Manage access, Move discussions, Archive.',
      },
      on: { JOIN: 'joined', MARK_ALL_READ: 'markAllReadConfirm', ARCHIVE: 'archiveConfirm' },
    },
    joined: {
      meta: {
        description:
          'After Join space the page itself does not change: no toast, no badge. Only the reopened menu now says "Leave space".',
      },
    },
    markAllReadConfirm: {
      meta: { description: 'The confirmation before marking every discussion in QA & Playtests as read.' },
      on: { CONFIRM_READ: 'allRead' },
    },
    allRead: {
      meta: {
        description:
          'After Mark all as read: the sidebar count beside QA & Playtests clears, but the list is not refetched, so the smoke-test row is still bold with its orange 6.',
      },
    },
    bulkMove: {
      meta: {
        description:
          'Move discussions mode: each row has a checkbox, the header offers Cancel and a disabled "Move discussions" until something is picked.',
      },
    },
    archiveConfirm: {
      meta: { description: 'The confirmation before archiving the space, saying it becomes read-only.' },
      on: { CONFIRM_ARCHIVE: 'archived' },
    },
    archived: {
      meta: {
        description:
          'The archived space: an "Archived" badge beside the name, no "Add new" button, and the space drops out of the sidebar. The list itself looks the same.',
      },
    },
    empty: {
      meta: { description: 'A new space with no discussions yet: the generic "No discussions" box under the tabs.' },
    },
    notFound: {
      meta: {
        description:
          'A space id that does not exist. The router sends it to the app-wide "Page not found" page before Space.vue mounts, so Space.vue\'s own "Page not found" box is not what shows.',
      },
    },
    spacesFailed: {
      meta: {
        description:
          'The global spaces list failed to load. The router cannot tell this from a missing space and shows the same "Page not found" page, saying the link is invalid or access was lost; the sidebar has no spaces.',
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
      await expect(scene.page.getByRole('button', { name: 'Load more' })).toBeVisible({ timeout: 30_000 })
    },
    async OPEN_MENU(scene) {
      await openMenu(scene)
      await expect(scene.page.getByRole('menuitem', { name: 'Join space' })).toBeVisible()
    },
    async JOIN(scene) {
      const joined = scene.page.waitForResponse((r) => r.url().includes('get_joined_spaces'))
      await pick(scene, 'Join space')
      await joined
      await openMenu(scene)
      await expect(scene.page.getByRole('menuitem', { name: 'Leave space' })).toBeVisible()
    },
    async MARK_ALL_READ(scene) {
      await pick(scene, 'Mark all as read')
      await expect(dialog(scene).getByText(`mark all discussions in ${SPACE_TITLE} as read`)).toBeVisible()
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
      await pick(scene, 'Archive')
      await expect(dialog(scene).getByText('archived space')).toBeVisible()
    },
    async CONFIRM_ARCHIVE(scene) {
      await dialog(scene).getByRole('button', { name: 'Archive' }).click()
      await expect(dialog(scene)).toBeHidden()
      await expect(scene.page.getByText('Archived', { exact: true })).toBeVisible()
      await expect(scene.page.getByRole('button', { name: 'Add new' })).toBeHidden()
    },
    async OPEN_EMPTY_SPACE(scene) {
      const empty = await scene.space(COMMUNITY)
      // A full navigation, so the spaces list is fetched again and includes the new space.
      await openSpace(scene, empty.name)
      await expect(scene.page.getByText('No discussions')).toBeVisible()
    },
    async OPEN_MISSING_SPACE(scene) {
      await openSpace(scene, '99999')
      await expect(scene.page.getByText('Page not found')).toBeVisible()
    },
    async SPACES_FAIL(scene) {
      const spacesList = await scene.hold(SPACES_LIST_URL)
      await spacesList.abort(500)
      await openSpace(scene, spaceIds.get(scene) as string)
      await expect(scene.page.getByText('Page not found')).toBeVisible({ timeout: 30_000 })
    },
  },
})
