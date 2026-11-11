import { expect } from '@playwright/test'
import { setup } from 'xstate'
import { defineFlow } from '../flow'
import { communities, type Hold, type Scene } from '../scene'

type Event =
  | { type: 'OPEN_SPACE_PICKER' }
  | { type: 'WRITE' }
  | { type: 'WRITE_OFFLINE' }
  | { type: 'PUBLISH' }
  | { type: 'PUBLISHED' }
  | { type: 'PUBLISH_FAILS' }
  | { type: 'LEAVE' }
  | { type: 'OPEN_DRAFT' }
  | { type: 'DRAFT_LOADS' }
  | { type: 'DRAFT_FAILS' }

/**
 * The discussion composer at /community/:id/new-discussion. In the code the
 * phase is spread over `useNewDiscussion.ts` (publishing,
 * isPublishingSuccessfully, publishError, errorMessage, isDeletingDraft) and
 * `useDraftSync.ts` (data === null for loading, owner, dirty, lastError).
 */
const machine = setup({ types: { events: {} as Event } }).createMachine({
  id: 'newDiscussion',
  initial: 'blank',
  states: {
    blank: {
      meta: {
        description:
          'A blank composer in Common Room: "New discussion" in the breadcrumb, a "Select space" picker with a folder icon in the header, an empty title, and Publish disabled.',
      },
      on: { OPEN_SPACE_PICKER: 'spacePicker', WRITE: 'filled', WRITE_OFFLINE: 'saveFailed', OPEN_DRAFT: 'draftLoading' },
    },
    spacePicker: {
      meta: { description: 'The space picker open: a "Search spaces" box over a list of every space Maya can post in, grouped by community.' },
    },
    filled: {
      meta: {
        description:
          'A title, a body and the Releases space filled in. The draft has saved itself, so the breadcrumb shows its title and Publish is enabled.',
      },
      on: { PUBLISH: 'publishing', LEAVE: 'leftToDrafts' },
    },
    saveFailed: {
      meta: {
        description:
          'Writing while draft saves fail: a toast says a local copy is kept and retried, and a red "Not saved" status sits next to Publish. The breadcrumb still says "New discussion".',
      },
    },
    publishing: {
      meta: { description: 'Publish is in flight: the Publish button spins at its usual width, and the solid chevron beside it ignores clicks.' },
      on: { PUBLISHED: 'posted', PUBLISH_FAILS: 'publishFailed' },
    },
    publishFailed: {
      meta: { description: 'Publishing failed: a red line above the title repeats the server\'s message ("Something went wrong.") with a Retry button, and the draft stays as it was.' },
    },
    posted: {
      meta: { description: 'Published: the composer is replaced by the new discussion in Releases.' },
    },
    leftToDrafts: {
      meta: {
        description: 'Leaving with unsaved text asks nothing: the draft flushes and Drafts lists it with the rest.',
      },
    },
    draftLoading: {
      meta: {
        description:
          "Opening Maya's saved draft while it loads: \"Loading draft…\" over an empty title, \"Loading…\" in the breadcrumb after Drafts, a dimmed toolbar and space picker, and no Publish button.",
      },
      on: { DRAFT_LOADS: 'draftRestored', DRAFT_FAILS: 'draftLoadFailed' },
    },
    draftRestored: {
      meta: { description: "Maya's saved draft restored: the Next Fest sprint plan in Releases, ready to keep editing." },
    },
    draftLoadFailed: {
      meta: {
        description:
          'The draft could not be loaded: "Could not load this draft." with a Retry button in place of the title and editor, "Draft" in the breadcrumb, a dimmed toolbar and space picker, and no Publish button.',
      },
    },
  },
})

const COMMUNITY = communities.commonRoom
const PUBLISH_URL = '**/*gp_draft.publish_draft*'
const DRAFT_WRITES = /\/api\/v2\/document\/GP(%20| )Draft/
const DRAFT_READ = /\/frappe\.client\.get(\?|$)/

const TITLE = 'Demo build freeze moves to Thursday'
const BODY = [
  'Kenji found a save-corruption bug in the library room late yesterday, so we are holding the freeze for two days.',
  'Everything that lands before Thursday 6pm goes into the Next Fest build. After that it is fixes only.',
]

const holds = new WeakMap<Scene, Hold>()

function title(scene: Scene) {
  return scene.page.getByPlaceholder('Title')
}

function publishButton(scene: Scene) {
  return scene.page.getByRole('button', { name: /Publish$/ }).filter({ visible: true })
}

function spaceTrigger(scene: Scene) {
  return scene.page.getByText('Select space').filter({ visible: true })
}

async function writePost(scene: Scene) {
  await title(scene).fill(TITLE)
  const body = scene.page.locator('.ProseMirror').filter({ visible: true }).first()
  await body.click()
  await expect(body).toBeFocused()
  await scene.page.keyboard.type(BODY[0])
  await scene.page.keyboard.press('Enter')
  await scene.page.keyboard.type(BODY[1])
  await spaceTrigger(scene).click()
  await scene.page.getByRole('option', { name: 'Releases' }).click()
}

/** Maya's draft from the demo. GP Draft rows are visible to their owner only, so ask as Maya. */
async function mayasDraft(scene: Scene): Promise<string> {
  const params = new URLSearchParams({
    filters: JSON.stringify({ title: ['like', 'Next Fest sprint%'] }),
    fields: '["name"]',
  })
  const response = await scene.api.get(`/api/resource/GP%20Draft?${params}`)
  if (!response.ok()) throw new Error(`Listing Maya's drafts failed: ${response.status()}`)
  const [row] = ((await response.json()) as { data: { name: string }[] }).data
  if (!row) throw new Error("Maya's Next Fest draft is missing from the demo")
  return String(row.name)
}

export const newDiscussion = defineFlow<Event>({
  id: 'newDiscussion',
  title: 'New discussion',
  source:
    'frontend/src/pages/NewDiscussion/useNewDiscussion.ts, frontend/src/data/useDraftSync.ts, frontend/src/pages/NewDiscussion/PublishControls.vue',
  machine,
  async enter(scene) {
    await scene.goto(`/community/${COMMUNITY}/new-discussion`)
    await expect(title(scene)).toBeEditable()
    await expect(spaceTrigger(scene)).toBeVisible()
  },
  events: {
    async OPEN_SPACE_PICKER(scene) {
      await spaceTrigger(scene).click()
      await expect(scene.page.getByRole('option', { name: 'Releases' })).toBeVisible()
    },
    async WRITE(scene) {
      await writePost(scene)
      await expect(scene.page).toHaveURL(/[?&]draft=/, { timeout: 15_000 })
      await expect(publishButton(scene)).toBeEnabled()
      await title(scene).click()
      await scene.page.mouse.move(700, 20)
    },
    async WRITE_OFFLINE(scene) {
      const hold = await scene.hold(DRAFT_WRITES)
      await hold.abort(500)
      await writePost(scene)
      await expect(scene.page.getByText('Could not save your draft to the server')).toBeVisible({ timeout: 30_000 })
      await expect(scene.page.getByText('Not saved', { exact: true }).filter({ visible: true })).toBeVisible()
      await scene.page.mouse.move(700, 20)
    },
    async PUBLISH(scene) {
      holds.set(scene, await scene.hold(PUBLISH_URL))
      await publishButton(scene).click()
      await expect(publishButton(scene)).toHaveAttribute('aria-busy', 'true')
      await scene.page.mouse.move(700, 20)
    },
    async PUBLISHED(scene) {
      await holds.get(scene)?.release()
      await expect(scene.page).toHaveURL(/\/discussion\/\d+/, { timeout: 15_000 })
      await expect(scene.page.getByText(BODY[1])).toBeVisible()
    },
    async PUBLISH_FAILS(scene) {
      await holds.get(scene)?.abort(500)
      await expect(publishButton(scene)).toBeEnabled({ timeout: 30_000 })
      const alert = scene.page.getByRole('alert').filter({ hasText: /went wrong|Could not/ })
      await expect(alert).toBeVisible()
      await expect(alert.getByRole('button', { name: 'Retry' })).toBeVisible()
    },
    async LEAVE(scene) {
      await title(scene).fill(`${TITLE} (Friday at the latest)`)
      await scene.page.getByRole('link', { name: 'Drafts' }).filter({ visible: true }).first().click()
      await expect(scene.page).toHaveURL(/\/drafts/)
      await expect(scene.page.getByText(`${TITLE} (Friday at the latest)`)).toBeVisible()
      await scene.page.mouse.move(700, 20)
    },
    async OPEN_DRAFT(scene) {
      const name = await mayasDraft(scene)
      holds.set(scene, await scene.hold(DRAFT_READ))
      await scene.goto(`/community/${COMMUNITY}/new-discussion?draft=${name}`)
      await expect(scene.page.getByText('Loading draft…')).toBeVisible()
      await expect(scene.page.getByText('Loading…', { exact: true }).filter({ visible: true })).toBeVisible()
    },
    async DRAFT_LOADS(scene) {
      await holds.get(scene)?.release()
      await expect(title(scene)).toHaveValue(/Next Fest sprint/)
      await expect(title(scene)).toBeEditable()
    },
    async DRAFT_FAILS(scene) {
      await holds.get(scene)?.abort(500)
      await expect(scene.page.getByText('Could not load this draft')).toBeVisible({ timeout: 30_000 })
      await expect(scene.page.getByRole('button', { name: 'Retry' })).toBeVisible()
      await expect(scene.page.getByText('Loading draft…')).toBeHidden()
    },
  },
})
