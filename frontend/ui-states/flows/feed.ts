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
  | { type: 'RETRY' }

/**
 * A community's discussion feed: the first load, its tabs, and its sort.
 * In the code this is `Discussions.vue` over `DiscussionFeedBar.vue` (tabs and
 * sort) and `DiscussionList.vue`, whose template picks skeleton rows, the
 * list, `LoadError` or the feed's empty box from `discussions.loading`,
 * `discussions.error` and `discussions.data?.length`.
 */
const machine = setup({ types: { events: {} as Event } }).createMachine({
  id: 'feed',
  initial: 'skeleton',
  states: {
    skeleton: {
      meta: { description: 'The feed request is still out: three skeleton rows under the tabs and the sort.' },
      on: { LOADS: 'recent', FAILS: 'failed' },
    },
    failed: {
      meta: {
        description:
          'The feed request failed: a cloud icon, "Could not load discussions." and a Retry button where the rows would be. No "Load more".',
      },
      on: { RETRY: 'retried' },
    },
    retried: {
      meta: {
        description:
          'After Retry: the feed is back as it loads normally, the Pinned group on top and every post below it. Retry reloads the pinned request along with the main list.',
      },
    },
    recent: {
      meta: {
        description:
          'All discussions in Common Room, sorted by "Latest activity": pinned posts on top, then every post, newest activity first. The header button reads "New discussion".',
      },
      on: { SHOW_PARTICIPATING: 'participating', SHOW_UNREAD: 'unread', SORT_BY_CREATED: 'sortedByCreated' },
    },
    participating: {
      meta: { description: 'The Participating tab: posts Maya wrote or replied to.' },
    },
    unread: {
      meta: { description: 'The Unread tab: posts by others that Maya has not opened, with the unread count after the tab label.' },
      on: { CATCH_UP: 'unreadEmpty' },
    },
    unreadEmpty: {
      meta: { description: 'The Unread tab once everything is read: a check icon, "You\'re caught up" and "Discussions with new activity will show up here.".' },
    },
    sortedByCreated: {
      meta: {
        description:
          'The same feed sorted by "Newest created": newest posts first, and each row\'s date is when the post was created, not its last activity.',
      },
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
      await expect(scene.page.getByText('Could not load discussions.')).toBeVisible({ timeout: 30_000 })
      await expect(scene.page.getByRole('button', { name: 'Retry' })).toBeVisible()
      await expect(scene.page.getByRole('button', { name: 'Load more' })).toBeHidden()
    },
    async RETRY(scene) {
      await holds.get(scene)?.release()
      await scene.page.getByRole('button', { name: 'Retry' }).click()
      await expect(scene.page.getByText('Pinned', { exact: true })).toBeVisible()
      await expect(rows(scene).nth(5)).toBeVisible()
      await expect(scene.page.getByText('Could not load discussions.')).toBeHidden()
      await scene.page.mouse.move(700, 20)
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
      await expect(scene.page.getByText("You're caught up")).toBeVisible()
    },
    async SORT_BY_CREATED(scene) {
      const sort = scene.page.getByRole('combobox').first()
      await sort.click()
      await scene.page.getByRole('option', { name: 'Newest created' }).click()
      await expect(sort).toContainText('Newest created')
      await expect(rows(scene).first()).toBeVisible()
      // The click leaves the pointer over the first row, which would show its hover.
      await scene.page.mouse.move(700, 20)
    },
  },
})
