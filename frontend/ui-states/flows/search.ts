import { expect } from '@playwright/test'
import { setup } from 'xstate'
import { defineFlow } from '../flow'
import type { Hold, Scene } from '../scene'

type Event =
  | { type: 'TYPE' }
  | { type: 'SUBMIT' }
  | { type: 'LOADS' }
  | { type: 'FAILS' }
  | { type: 'SEARCH_MISS' }
  | { type: 'OPEN_AUTHOR_MENU' }
  | { type: 'PICK_AUTHOR' }
  | { type: 'PICK_ABSENT_AUTHOR' }
  | { type: 'FILTER_SPACE' }
  | { type: 'FILTER_COMMUNITY' }
  | { type: 'REFINED' }
  | { type: 'RETRY' }

/**
 * Full-text search at /search. In the code the summary line is a v-if chain
 * in `Search.vue` over `search.error`, `newSearch && query.length > 3`,
 * `search.loading` and `searchResponse.summary`; the result list renders
 * `searchResponse` on its own, whatever that chain shows.
 */
const machine = setup({ types: { events: {} as Event } }).createMachine({
  id: 'search',
  initial: 'empty',
  states: {
    empty: {
      meta: {
        description:
          'No query yet: the search box with "Search discussions and comments", the four filter buttons (Author, Space, Community, Tags), and nothing below them.',
      },
      on: { TYPE: 'typed', SEARCH_MISS: 'noResults' },
    },
    typed: {
      meta: {
        description: 'A query typed but not sent: "Press enter to search" under the filters.',
      },
      on: { SUBMIT: 'searching' },
    },
    searching: {
      meta: {
        description: 'The search request is out: a spinner with "Searching…" and no rows yet.',
      },
      on: { LOADS: 'results', FAILS: 'failed' },
    },
    failed: {
      meta: {
        description:
          'The search failed: "Search failed. Try again." with a Retry button where the results would be, and no summary line.',
      },
      on: { RETRY: 'results' },
    },
    results: {
      meta: {
        description:
          'Results for "capsule": the match count and time, a "Helpful?" prompt, and discussions, tasks and comments with the word highlighted.',
      },
      on: {
        OPEN_AUTHOR_MENU: 'authorMenu',
        FILTER_SPACE: 'refining',
        FILTER_COMMUNITY: 'byCommunity',
      },
    },
    noResults: {
      meta: {
        description:
          'A query with no matches: "0 matches" in the summary line and a "No results" box suggesting different words or fewer filters.',
      },
    },
    authorMenu: {
      meta: {
        description:
          'The Author filter open over the results: every user, with a count of all their indexed posts (not of matches for this query) beside the name.',
      },
      on: { PICK_AUTHOR: 'byAuthor', PICK_ABSENT_AUTHOR: 'filterEmpty' },
    },
    byAuthor: {
      meta: {
        description:
          'Filtered to Lena Sorensen: her four capsule posts, tasks and replies, with "1 filter" and a "Clear filters" button.',
      },
    },
    filterEmpty: {
      meta: {
        description:
          'Filtered to Felix, whom the menu credits with posts but who never wrote about the capsule: "0 matches • 1 filter", "Clear filters", and the "No results" box.',
      },
    },
    bySpace: {
      meta: {
        description:
          'Filtered to the Art space: the Space button names it, only Art results remain, and the summary says "1 filter" with "Clear filters".',
      },
    },
    byCommunity: {
      meta: {
        description:
          'Filtered to Community & Marketing: only results from its spaces remain, with "1 filter" and "Clear filters".',
      },
    },
    refining: {
      meta: {
        description:
          'Space set to Art while the new request is out: "Searching…" above the previous, unfiltered results.',
      },
      on: { REFINED: 'bySpace' },
    },
  },
})

const SEARCH_URL = '**/api/v2/method/gameplan.api.search_sqlite*'
const QUERY = 'capsule'
const MISS = 'xylophone'

const holds = new WeakMap<Scene, Hold>()

function input(scene: Scene) {
  return scene.page.getByPlaceholder('Search discussions and comments')
}

function summary(scene: Scene) {
  return scene.page.getByText(/\d+ match(es)? \(/)
}

function rows(scene: Scene) {
  return scene.page.locator('a[href*="/discussion/"]')
}

function filterButton(scene: Scene, label: string) {
  return scene.page.getByRole('button', { name: label, exact: true })
}

/** Opens a filter, picks one option, and closes the menu again. */
async function pick(scene: Scene, filter: string, option: RegExp) {
  await filterButton(scene, filter).click()
  await scene.page.getByRole('option', { name: option }).click()
  await scene.page.keyboard.press('Escape')
  await expect(scene.page.getByRole('listbox')).toBeHidden()
}

async function runSearch(scene: Scene, query: string) {
  await input(scene).fill(query)
  await input(scene).press('Enter')
}

async function filtered(scene: Scene, count: RegExp) {
  await expect(scene.page.getByText(/• 1 filter\b/)).toBeVisible()
  await expect(scene.page.getByRole('button', { name: 'Clear filters' })).toBeVisible()
  await expect(summary(scene)).toHaveText(count)
  await scene.page.mouse.move(700, 20)
}

export const search = defineFlow<Event>({
  id: 'search',
  title: 'Search',
  source: 'frontend/src/pages/Search.vue',
  machine,
  async enter(scene) {
    await scene.goto('/search')
    await expect(input(scene)).toBeVisible()
    await expect(filterButton(scene, 'Author')).toBeVisible()
  },
  events: {
    async TYPE(scene) {
      await input(scene).pressSequentially(QUERY)
      await expect(scene.page.getByText('Press enter to search')).toBeVisible()
    },
    async SUBMIT(scene) {
      holds.set(scene, await scene.hold(SEARCH_URL))
      await input(scene).press('Enter')
      await expect(scene.page.getByText('Searching…')).toBeVisible()
    },
    async LOADS(scene) {
      await holds.get(scene)?.release()
      await expect(summary(scene)).toBeVisible()
      await expect(rows(scene).first()).toBeVisible()
    },
    async FAILS(scene) {
      await holds.get(scene)?.abort(500)
      await expect(scene.page.getByRole('button', { name: 'Retry' })).toBeVisible({
        timeout: 30_000,
      })
      await expect(summary(scene)).toBeHidden()
    },
    async RETRY(scene) {
      await holds.get(scene)?.release()
      await scene.page.getByRole('button', { name: 'Retry' }).click()
      await expect(summary(scene)).toBeVisible()
      await expect(rows(scene).first()).toBeVisible()
    },
    async SEARCH_MISS(scene) {
      await runSearch(scene, MISS)
      await expect(summary(scene)).toHaveText(/^0 matches/)
      await expect(scene.page.getByText('No results', { exact: true })).toBeVisible()
    },
    async OPEN_AUTHOR_MENU(scene) {
      await filterButton(scene, 'Author').click()
      await expect(scene.page.getByRole('option', { name: /^Lena Sorensen/ })).toBeVisible()
    },
    async PICK_AUTHOR(scene) {
      await scene.page.getByRole('option', { name: /^Lena Sorensen/ }).click()
      await scene.page.keyboard.press('Escape')
      await filtered(scene, /^[1-9]\d* match/)
    },
    async PICK_ABSENT_AUTHOR(scene) {
      await scene.page
        .getByRole('option', { name: /^Felix Novak/ })
        .filter({ hasText: /\d/ })
        .click()
      await scene.page.keyboard.press('Escape')
      await filtered(scene, /^0 matches/)
    },
    async FILTER_SPACE(scene) {
      holds.set(scene, await scene.hold(SEARCH_URL))
      await pick(scene, 'Space', /^Art\b/)
      await expect(scene.page.getByText('Searching…')).toBeVisible()
      await scene.page.mouse.move(700, 20)
    },
    async FILTER_COMMUNITY(scene) {
      await pick(scene, 'Community', /^Community & Marketing/)
      await filtered(scene, /^[1-9]\d* match/)
    },
    async REFINED(scene) {
      await holds.get(scene)?.release()
      await filtered(scene, /^[1-9]\d* match/)
    },
  },
})
