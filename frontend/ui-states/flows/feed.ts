import { expect } from '@playwright/test'
import { setup } from 'xstate'
import { spacesOf } from '../content'
import { defineFlow } from '../flow'
import { communities, type Hold, type Scene } from '../scene'

type Event =
  | { type: 'LOADS' }
  | { type: 'FAILS' }
  | { type: 'SHOW_PARTICIPATING' }
  | { type: 'SHOW_UNREAD' }
  | { type: 'CATCH_UP' }
  | { type: 'SORT_BY_CREATED' }

/**
 * A community's discussion feed: the first load, its tabs, and its sort.
 * In the code this is `Discussions.vue` over `DiscussionList.vue`, whose
 * template picks skeleton rows, the list, or "No discussions" from
 * `discussions.loading` and `discussions.data?.length`.
 */
const machine = setup({ types: { events: {} as Event } }).createMachine({
  id: 'feed',
  initial: 'skeleton',
  states: {
    skeleton: {
      meta: { description: 'The feed request is still out: three skeleton rows under the tabs.' },
      on: { LOADS: 'recent', FAILS: 'failed' },
    },
    failed: {
      meta: {
        description:
          'The feed request failed. No error and no rows: only a "Load more" button under the tabs.',
      },
    },
    recent: {
      meta: { description: 'All Discussions in Common Room: pinned posts on top, then every post, newest activity first.' },
      on: { SHOW_PARTICIPATING: 'participating', SHOW_UNREAD: 'unread', SORT_BY_CREATED: 'sortedByCreated' },
    },
    participating: {
      meta: { description: 'Participating: posts Maya wrote or replied to.' },
    },
    unread: {
      meta: { description: 'Unread: posts by others that Maya has not opened, with the count beside the tab.' },
      on: { CATCH_UP: 'unreadEmpty' },
    },
    unreadEmpty: {
      meta: { description: 'Unread once everything is read: the generic "No discussions" box.' },
    },
    sortedByCreated: {
      meta: { description: 'The same feed sorted by when each post was created instead of by its last activity.' },
    },
  },
})

const holds = new WeakMap<Scene, Hold>()

const FEED_URL = '**/api/v2/method/gameplan.gameplan.doctype.gp_discussion.api.get_discussions*'
const COMMUNITY = communities.commonRoom

function rows(scene: Scene) {
  return scene.page.locator('a[href*="/discussion/"]')
}

async function openTab(scene: Scene, label: string) {
  await scene.page.getByRole('radio', { name: new RegExp(`^${label}`) }).first().click()
}

export const feed = defineFlow<Event>({
  id: 'feed',
  title: 'Community feed',
  source: 'frontend/src/pages/Discussions.vue, frontend/src/components/DiscussionList.vue',
  machine,
  async enter(scene) {
    holds.set(scene, await scene.hold(FEED_URL))
    await scene.goto(`/community/${COMMUNITY}/discussions`)
    await expect(scene.page.getByLabel('Loading discussion').first()).toBeVisible()
  },
  events: {
    async LOADS(scene) {
      await holds.get(scene)?.release()
      await expect(scene.page.getByText('Pinned', { exact: true })).toBeVisible()
      await expect(rows(scene).nth(5)).toBeVisible()
    },
    async FAILS(scene) {
      await holds.get(scene)?.abort(500)
      await expect(scene.page.getByRole('button', { name: 'Load more' })).toBeVisible({ timeout: 30_000 })
    },
    async SHOW_PARTICIPATING(scene) {
      await openTab(scene, 'Participating')
      await expect(scene.page).toHaveURL(/\/participating$/)
      await expect(rows(scene).first()).toBeVisible()
    },
    async SHOW_UNREAD(scene) {
      await openTab(scene, 'Unread')
      await expect(scene.page).toHaveURL(/\/unread$/)
      await expect(rows(scene).first()).toBeVisible()
    },
    async CATCH_UP(scene) {
      for (const space of await spacesOf(scene, COMMUNITY)) {
        await scene.method(scene.api, 'GP Project', space, 'mark_all_as_read')
      }
      await scene.page.reload()
      await expect(scene.page.getByText('No discussions')).toBeVisible()
    },
    async SORT_BY_CREATED(scene) {
      const sort = scene.page.getByRole('combobox').first()
      await sort.click()
      await scene.page.getByRole('option', { name: 'Creation date' }).click()
      await expect(sort).toContainText('Creation date')
      await expect(rows(scene).first()).toBeVisible()
      // The click leaves the pointer over the first row, which would show its hover.
      await scene.page.mouse.move(700, 20)
    },
  },
})
