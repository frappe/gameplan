import { expect } from '@playwright/test'
import { setup } from 'xstate'
import { defineFlow } from '../flow'
import type { Hold, Person, Scene } from '../scene'

type Event =
  | { type: 'LOADS' }
  | { type: 'FAILS' }
  | { type: 'MARK_ONE_READ' }
  | { type: 'SHOW_READ' }
  | { type: 'MARK_ALL' }
  | { type: 'CONFIRM' }
  | { type: 'AS_NEWCOMER' }

/**
 * The notifications inbox. In the code this is `Notifications.vue`, which
 * keeps two lists (unread, read) and picks skeleton rows, the active list, or
 * an empty box from `activeList.loading`, `activeList.data?.length` and the
 * active tab. The rail's badge is a third request, `unreadNotifications`.
 */
const machine = setup({ types: { events: {} as Event } }).createMachine({
  id: 'notifications',
  initial: 'skeleton',
  states: {
    skeleton: {
      meta: { description: 'The unread list request is still out: three skeleton rows under the Unread and Read tabs.' },
      on: { LOADS: 'unread', FAILS: 'failed' },
    },
    failed: {
      meta: {
        description:
          'The unread list failed. No error and no retry: the page says "You\'re caught up" while the bell on the rail still shows its unread dot.',
      },
    },
    unread: {
      meta: {
        description:
          'Unread tab: Maya\'s four newest notifications (all reactions to her posts) in medium weight, each with a check button in the right gutter, "Mark all as read" in the toolbar and a red dot on the rail\'s bell.',
      },
      on: { MARK_ONE_READ: 'markedOneRead', SHOW_READ: 'read', MARK_ALL: 'confirmMarkAll', AS_NEWCOMER: 'newcomer' },
    },
    markedOneRead: {
      meta: { description: 'After the check button on the first row: that notification leaves the Unread list with no toast or undo; three remain and the bell keeps its dot.' },
    },
    read: {
      meta: { description: 'Read tab: the notifications Maya has already handled, in regular weight, with no check buttons and no "Mark all as read". The bell keeps its dot for the unread ones.' },
    },
    confirmMarkAll: {
      meta: { description: '"Mark all as read" asks first, in a red danger dialog that warns it cannot be undone.' },
      on: { CONFIRM: 'caughtUp' },
    },
    caughtUp: {
      meta: { description: 'After marking all read: the "You\'re caught up" box, no "Mark all as read" button, and no dot on the rail\'s bell.' },
    },
    newcomer: {
      meta: {
        description:
          'Felix, with his read notifications cleared to stand in for a newcomer, on the Read tab: the "No read notifications" box. The bell keeps its dot for his unread ones.',
      },
    },
  },
})

const holds = new WeakMap<Scene, Hold>()

/** The two `useList` reads of GP Notification; writes go to `/GP Notification/<name>` and do not match. */
const LIST_URL = /\/api\/v2\/document\/GP(%20| )Notification\?/

function unreadRows(scene: Scene) {
  return scene.page.locator('button:has(.lucide-check)')
}

/**
 * Felix's visits in the demo mark some notifications read; a newcomer has none.
 * GP Notification lists only the session user's own rows, even for the
 * Administrator, so the names come from Felix's session.
 */
async function clearReadNotifications(scene: Scene, person: Person) {
  const own = await scene.as(person)
  const params = new URLSearchParams({
    filters: JSON.stringify({ to_user: person.email, read: 1 }),
    fields: '["name"]',
    limit_page_length: '0',
  })
  const response = await own.get(`/api/resource/GP%20Notification?${params}`)
  if (!response.ok()) throw new Error(`Listing notifications of ${person.email} failed: ${response.status()}`)
  const { data } = (await response.json()) as { data: { name: string | number }[] }
  for (const { name } of data) {
    const deleted = await scene.admin.delete(`/api/resource/GP%20Notification/${name}`)
    if (!deleted.ok()) throw new Error(`Deleting notification ${name} failed: ${deleted.status()}`)
  }
}

async function openTab(scene: Scene, label: string) {
  await scene.page.getByRole('radio', { name: label, exact: true }).click()
}

export const notifications = defineFlow<Event>({
  id: 'notifications',
  title: 'Notifications',
  source: 'frontend/src/pages/Notifications.vue, frontend/src/data/notifications.ts, frontend/src/components/AppRail/AppRail.vue',
  machine,
  async enter(scene) {
    holds.set(scene, await scene.hold(LIST_URL))
    await scene.goto('/notifications')
    await expect(scene.page.getByLabel('Loading notification').first()).toBeVisible()
  },
  events: {
    async LOADS(scene) {
      await holds.get(scene)?.release()
      await expect(unreadRows(scene).first()).toBeVisible()
      await expect(scene.page.getByRole('button', { name: 'Mark all as read' })).toBeVisible()
    },
    async FAILS(scene) {
      await holds.get(scene)?.abort(500)
      await expect(scene.page.getByText("You're caught up")).toBeVisible({ timeout: 30_000 })
    },
    async MARK_ONE_READ(scene) {
      const before = await unreadRows(scene).count()
      await unreadRows(scene).first().click()
      await expect(unreadRows(scene)).toHaveCount(before - 1)
      await scene.page.mouse.move(700, 20)
    },
    async SHOW_READ(scene) {
      await openTab(scene, 'Read')
      await expect(scene.page.getByRole('button', { name: 'Mark all as read' })).toBeHidden()
      await expect(scene.page.locator('a[href*="/discussion/"]').first()).toBeVisible()
      await scene.page.mouse.move(700, 20)
    },
    async MARK_ALL(scene) {
      await scene.page.getByRole('button', { name: 'Mark all as read' }).click()
      await expect(scene.page.getByRole('dialog')).toContainText('You cannot undo this')
    },
    async CONFIRM(scene) {
      await scene.page.getByRole('dialog').getByRole('button', { name: 'Mark all as read' }).click()
      await expect(scene.page.getByRole('dialog')).toBeHidden()
      await expect(scene.page.getByText("You're caught up")).toBeVisible()
      await scene.page.mouse.move(700, 20)
    },
    async AS_NEWCOMER(scene) {
      await clearReadNotifications(scene, scene.people.member)
      await scene.signIn(scene.people.member)
      await scene.goto('/notifications')
      await openTab(scene, 'Read')
      await expect(scene.page.getByText('No read notifications')).toBeVisible()
    },
  },
})
