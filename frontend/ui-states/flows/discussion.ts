import { expect } from '@playwright/test'
import { setup } from 'xstate'
import { reply } from '../content'
import { defineFlow } from '../flow'
import { communities, type Hold, type Scene } from '../scene'

type Event =
  | { type: 'LOADS' }
  | { type: 'FAILS' }
  | { type: 'NEW_REPLY' }
  | { type: 'OPEN_COMPOSER' }
  | { type: 'SUBMIT' }
  | { type: 'POST_FAILS' }
  | { type: 'EDIT' }
  | { type: 'OPEN_REACTIONS' }
  | { type: 'OPEN_OPTIONS' }
  | { type: 'CLOSE' }
  | { type: 'CONFIRM_CLOSE' }
  | { type: 'OPEN_POLL' }
  | { type: 'OPEN_MISSING' }

/**
 * One discussion thread: the post, its timeline of replies, activities and
 * polls, and the fixed reply composer. `DiscussionView.vue` picks the skeleton,
 * the thread, "Discussion not found" or "Could not load this discussion" from
 * `discussion.loading`, `discussion.doc`, the error type and `isFinished`;
 * `CommentsArea.vue` shows the composer as a button, a minimised bar or the
 * open editor from `showCommentBox` and `composerMinimized`.
 */
const machine = setup({ types: { events: {} as Event } }).createMachine({
  id: 'discussion',
  initial: 'loading',
  states: {
    loading: {
      meta: {
        description:
          'Opened from the Releases list while the discussion is still loading: a pulsing avatar and three grey title bars, though the breadcrumb already shows the full title from a copy the client holds.',
      },
      on: { LOADS: 'read', FAILS: 'failed' },
    },
    failed: {
      meta: {
        description:
          'The discussion request failed with a 500, yet the thread renders as if it had loaded, with no error: the page already had a copy of the post in frappe-ui\'s document store, and DiscussionView checks for a doc before it checks for an error. "Could not load this discussion" never shows on this path.',
      },
    },
    read: {
      meta: {
        description:
          'Maya\'s own checklist post, read, scrolled to its latest reply, with the "Add a comment" bar fixed at the bottom.',
      },
      on: {
        NEW_REPLY: 'unread',
        OPEN_COMPOSER: 'composerOpen',
        EDIT: 'editing',
        OPEN_REACTIONS: 'reactionPicker',
        OPEN_OPTIONS: 'optionsMenu',
        OPEN_POLL: 'poll',
        OPEN_MISSING: 'missing',
      },
    },
    unread: {
      meta: {
        description:
          'Priya replied since Maya last read the thread: a "New comments" divider sits above her reply.',
      },
    },
    composerOpen: {
      meta: { description: 'The reply composer open with a reply typed in, Discard and Submit under it.' },
      on: { SUBMIT: 'posting' },
    },
    posting: {
      meta: { description: 'The reply is being saved: the Submit button spins and the text stays in the editor.' },
      on: { POST_FAILS: 'postFailed' },
    },
    postFailed: {
      meta: {
        description:
          'Saving the reply failed: a bare red "Internal Server Error" under the editor toolbar, with the reply text kept and Submit ready to try again.',
      },
    },
    editing: {
      meta: {
        description:
          'Editing the post in place: the post gets a border, the title becomes an input and the body editable, with Save and Discard below the fold. The reply bar is hidden.',
      },
    },
    reactionPicker: {
      meta: { description: 'The emoji picker open under the post, from the smiley button.' },
    },
    optionsMenu: {
      meta: {
        description:
          'The post\'s options menu for its author: Edit, Revisions, Copy link, Mark as unread, Bookmark, Pin, Close, Move to and Delete.',
      },
      on: { CLOSE: 'closeConfirm' },
    },
    closeConfirm: {
      meta: { description: 'The confirmation before closing the discussion, saying replies will be disabled.' },
      on: { CONFIRM_CLOSE: 'closed' },
    },
    closed: {
      meta: {
        description:
          'The closed discussion: a lock before the title, and the "Add a comment" bar is gone with nothing in its place to say why.',
      },
    },
    poll: {
      meta: { description: 'A poll in the timeline under the post: "Which lobby rug?" with 10 votes, four options Maya has not voted on, and Stop Poll for its author. (The demo leaves it open, though a later reply says it closed.)' },
    },
    missing: {
      meta: {
        description:
          'A link to a discussion that does not exist. The router answers before the page loads, with the app-wide "Page not found", not the discussion page\'s own "Discussion not found".',
      },
    },
  },
})

const holds = new WeakMap<Scene, Hold>()
const discussionIds = new WeakMap<Scene, string>()

const COMMUNITY = communities.commonRoom
const SPACE_TITLE = 'Releases'
const POST_TITLE = 'Next Fest demo scope: the checklist'
const POLL_POST_TITLE = 'Settling the lobby rug once and for all (poll)'
const DOC_URL = (name: string) => new RegExp(`/api/v2/document/GP(%20| )Discussion/${name}(\\?|$)`)
const NEW_COMMENT_URL = /\/api\/v2\/document\/GP(%20| )Comment(\?|$)/

const REPLY_TEXT =
  'Added a row for the controller remap screen. Felix has it working on Steam Deck, so it can come off the risk list.'

function composer(scene: Scene) {
  return scene.page.locator('[data-comment-composer-surface]')
}

const spaceIds = new WeakMap<Scene, string>()
function spaceOf(scene: Scene): string {
  return spaceIds.get(scene) as string
}

/** Whether the page's scroll container rests at its bottom, where the thread scrolls itself on load. */
function scrolledToEnd(scene: Scene) {
  return scene.page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>('*')].some(
      (el) => el.scrollTop > 0 && el.scrollTop + el.clientHeight >= el.scrollHeight - 2,
    ),
  )
}

async function waitForThread(scene: Scene) {
  await expect(scene.page.getByRole('heading', { level: 1, name: POST_TITLE })).toBeAttached()
  await expect(scene.page.getByRole('button', { name: 'Add a comment' })).toBeVisible()
  // The thread jumps to its last reply once replies load; wait for that before acting on the post.
  await expect.poll(() => scrolledToEnd(scene)).toBe(true)
  await scene.settle(300)
}

/** Brings the post's own header back into view, as clicking its title in the breadcrumb does. */
async function scrollToPost(scene: Scene) {
  await scene.page.getByRole('heading', { level: 1, name: POST_TITLE }).scrollIntoViewIfNeeded()
  await scene.settle(200)
}

export const discussion = defineFlow<Event>({
  id: 'discussion',
  title: 'Discussion page',
  source:
    'frontend/src/pages/SpaceDiscussion.vue, frontend/src/components/DiscussionView.vue, frontend/src/components/CommentsArea.vue, frontend/src/router.ts',
  machine,
  async enter(scene) {
    const space = await scene.find('GP Project', { title: SPACE_TITLE })
    const name = await scene.find('GP Discussion', { title: POST_TITLE })
    spaceIds.set(scene, space)
    discussionIds.set(scene, name)
    await scene.goto(`/community/${COMMUNITY}/space/${space}/discussions`)
    const row = scene.page.locator('a[href*="/discussion/"]').filter({ hasText: POST_TITLE })
    await expect(row).toBeVisible()
    // In-app navigation skips the router's own fetch, so the page's skeleton shows.
    holds.set(scene, await scene.hold(DOC_URL(name)))
    await row.click()
    await expect(scene.page.locator('h1.animate-pulse')).toBeVisible()
    await scene.page.mouse.move(700, 20)
  },
  events: {
    async LOADS(scene) {
      await holds.get(scene)?.release()
      await waitForThread(scene)
    },
    async FAILS(scene) {
      const failed = scene.page.waitForResponse((r) => DOC_URL(discussionIds.get(scene) as string).test(r.url()))
      await holds.get(scene)?.abort(500)
      expect((await failed).status()).toBe(500)
      // No error box appears: the thread renders from the copy already in the client's store.
      await waitForThread(scene)
      await expect(scene.page.getByText('Could not load this discussion')).toBeHidden()
    },
    async NEW_REPLY(scene) {
      const priya = await scene.as(scene.people.peer)
      await reply(scene, priya, discussionIds.get(scene) as string, [REPLY_TEXT])
      await scene.page.reload()
      await waitForThread(scene)
      await expect(scene.page.getByRole('separator').filter({ hasText: 'New comments' })).toBeVisible()
    },
    async OPEN_COMPOSER(scene) {
      await scene.page.getByRole('button', { name: 'Add a comment' }).click()
      const editor = composer(scene).locator('[contenteditable="true"]')
      await expect(editor).toBeVisible()
      await editor.click()
      await scene.page.keyboard.type(
        'Store page copy is locked. Only open item is the capsule art, Lena is on it today.',
      )
      await expect(composer(scene).getByRole('button', { name: 'Submit' })).toBeEnabled()
    },
    async SUBMIT(scene) {
      holds.set(scene, await scene.hold(NEW_COMMENT_URL))
      const submit = composer(scene).getByRole('button', { name: 'Submit' })
      await submit.click()
      await expect(submit).toHaveAttribute('aria-busy', 'true')
      await scene.page.mouse.move(700, 20)
    },
    async POST_FAILS(scene) {
      await holds.get(scene)?.abort(500)
      await expect(composer(scene).getByRole('alert')).toBeVisible({ timeout: 60_000 })
    },
    async EDIT(scene) {
      await scrollToPost(scene)
      await scene.page.getByRole('button', { name: 'Discussion Options' }).click()
      await scene.page.getByRole('menuitem', { name: 'Edit' }).click()
      await expect(scene.page.getByPlaceholder('Title')).toBeVisible()
      await expect(scene.page.getByRole('button', { name: 'Add a comment' })).toBeHidden()
    },
    async OPEN_REACTIONS(scene) {
      await scrollToPost(scene)
      const add = scene.page.getByRole('button', { name: 'Add a reaction' }).first()
      await add.scrollIntoViewIfNeeded()
      await add.click()
      await expect(scene.page.getByRole('button', { name: '👍' }).first()).toBeVisible()
    },
    async OPEN_OPTIONS(scene) {
      await scrollToPost(scene)
      await scene.page.getByRole('button', { name: 'Discussion Options' }).click()
      await expect(scene.page.getByRole('menuitem', { name: 'Close discussion...' })).toBeVisible()
    },
    async CLOSE(scene) {
      await scene.page.getByRole('menuitem', { name: 'Close discussion...' }).click()
      await expect(scene.page.getByRole('dialog').getByText('commenting is disabled')).toBeVisible()
    },
    async CONFIRM_CLOSE(scene) {
      // The dialog's X is also labelled "Close"; the confirm button is the one with the text.
      await scene.page.getByRole('dialog').locator('button').filter({ hasText: /^\s*Close\s*$/ }).click()
      await expect(scene.page.getByRole('dialog')).toBeHidden()
      await expect(scene.page.getByRole('button', { name: 'Add a comment' })).toBeHidden()
      await expect(scene.page.locator('h1 .lucide-lock')).toBeVisible()
    },
    async OPEN_POLL(scene) {
      const name = await scene.find('GP Discussion', { title: POLL_POST_TITLE })
      const space = await scene.find('GP Project', { title: 'Game Design' })
      await scene.goto(`/community/${COMMUNITY}/space/${space}/discussion/${name}`)
      const poll = scene.page.getByText('Which lobby rug?').first()
      await expect(poll).toBeAttached()
      // Let the thread finish its own jump to the last reply before scrolling back to the poll.
      await expect.poll(() => scrolledToEnd(scene)).toBe(true)
      await scene.settle(300)
      await poll.scrollIntoViewIfNeeded()
      await expect(poll).toBeInViewport()
    },
    async OPEN_MISSING(scene) {
      await scene.goto(`/community/${COMMUNITY}/space/${spaceOf(scene)}/discussion/99999`)
      await expect(scene.page.getByText('Page not found')).toBeVisible()
    },
  },
})
