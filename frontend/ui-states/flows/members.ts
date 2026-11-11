import { expect, type Page } from '@playwright/test'
import { setup } from 'xstate'
import { defineFlow } from '../flow'
import type { Hold, Scene } from '../scene'

type Event =
  | { type: 'LOADS' }
  | { type: 'FAILS' }
  | { type: 'SEARCH_MISS' }
  | { type: 'OPEN_PROFILE' }
  | { type: 'OPEN_MISSING_PROFILE' }
  | { type: 'MANAGE_USERS' }
  | { type: 'PICK_ADMIN_ROLE' }
  | { type: 'OPEN_INVITE' }
  | { type: 'TYPE_EMAILS' }
  | { type: 'SEND' }
  | { type: 'SENT' }
  | { type: 'SEND_FAILS' }
  | { type: 'INVITEE_OPENS_LINK' }
  | { type: 'INVITEE_OPENS_BROKEN_LINK' }

/**
 * The People directory, a person's profile, and inviting someone new, as
 * Maya (a Gameplan Admin) in the Moonhollow demo. The invitee's side runs in
 * a second browser that is not signed in.
 */
const machine = setup({ types: { events: {} as Event } }).createMachine({
  id: 'members',
  initial: 'directoryLoading',
  states: {
    directoryLoading: {
      meta: {
        description:
          'The People list request is still out. The heading already says "0 members", and under the column headers there is only a spinning "Load more" button: no skeleton rows.',
      },
      on: { LOADS: 'directory', FAILS: 'directoryFailed' },
    },
    directoryFailed: {
      meta: {
        description:
          'The People list request failed. The heading still says "0 members", with "Internal Server Error" in red and a "Load more" button where the rows would be.',
      },
    },
    directory: {
      meta: {
        description:
          'People: 16 members, Maya first, then by last update, with post, reply and reaction counts. Admins see an Invite button.',
      },
      on: {
        SEARCH_MISS: 'searchEmpty',
        OPEN_PROFILE: 'profile',
        OPEN_MISSING_PROFILE: 'profileMissing',
        MANAGE_USERS: 'usersSettings',
      },
    },
    searchEmpty: {
      meta: { description: 'A search that matches nobody: "0 members" and "No members match your search".' },
    },
    profile: {
      meta: { description: "Priya Sharma's profile: Profile, Posts and Replies tabs over her cover, avatar, name and bio cards." },
    },
    profileMissing: {
      meta: { description: 'A profile link for someone who is not here: the generic "Page not found" box, with no way back to People.' },
    },
    usersSettings: {
      meta: {
        description:
          'Invite on People opens Settings at Users: everyone with a role picker, the date they joined, and a disable button.',
      },
      on: { OPEN_INVITE: 'inviteOpen', PICK_ADMIN_ROLE: 'roleConfirm' },
    },
    roleConfirm: {
      meta: {
        description:
          'Picking Admin for Priya asks to confirm, naming the role by its internal value, "Gameplan Admin", not the "Admin" label just picked.',
      },
    },
    inviteOpen: {
      meta: { description: 'The Invite People dialog over Users: an empty email box, with no role or button until something is typed.' },
      on: { TYPE_EMAILS: 'inviteFilled' },
    },
    inviteFilled: {
      meta: {
        description:
          'Two addresses typed: the Role picker (User by default), what that role can do, and the Invite button appear.',
      },
      on: { SEND: 'inviteSending' },
    },
    inviteSending: {
      meta: { description: 'Invite was clicked and the request is out: the button spins, and the email box is disabled and shows empty although the two addresses are being sent.' },
      on: { SENT: 'inviteSent', SEND_FAILS: 'inviteFailed' },
    },
    inviteSent: {
      meta: {
        description:
          'The invitations went out: the role picker and button go away, a summary says "2 invitations sent", and the pending invites are listed.',
      },
      on: { INVITEE_OPENS_LINK: 'setPassword', INVITEE_OPENS_BROKEN_LINK: 'linkInvalid' },
    },
    inviteFailed: {
      meta: { description: 'The invite request failed: "Internal Server Error" above the Invite button. The email box looks empty, yet Role and Invite stay because the addresses are still held; Invite would resend them unseen.' },
    },
    setPassword: {
      meta: {
        description:
          "Nadia opens her invitation link in a browser that is not signed in. The link creates her account and lands on Frappe's Set Password page, not a Gameplan screen.",
      },
    },
    linkInvalid: {
      meta: {
        description:
          'An invitation link whose key is cut short: a plain Frappe page, "This invitation link is no longer valid", "Status: 404" and a Home button.',
      },
    },
  },
})

const holds = new WeakMap<Scene, Hold>()
/** A browser with no session, for what an invitee sees before they have an account. */
const visitors = new WeakMap<Scene, Page>()

const PEOPLE_URL = '**/api/v2/method/gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.get_list*'
const INVITE_URL = '**/api/v2/method/gameplan.api.invite_by_email*'
const INVITEES = ['nadia@moonhollow.studio', 'omar@moonhollow.studio']

function settingsDialog(scene: Scene) {
  return scene.page.getByRole('dialog').first()
}

function inviteDialog(scene: Scene) {
  return scene.page.getByRole('dialog').filter({ hasText: 'Invite People' }).last()
}

async function visitor(scene: Scene): Promise<Page> {
  const existing = visitors.get(scene)
  if (existing) return existing
  const browser = scene.context.browser()
  if (!browser) throw new Error('The scene has no browser to open a visitor context in')
  const context = await browser.newContext({
    baseURL: scene.baseURL,
    viewport: { width: 1440, height: 900 },
    colorScheme: 'light',
  })
  // Close the visitor's browser together with the scene's.
  scene.page.once('close', () => void context.close())
  const page = await context.newPage()
  visitors.set(scene, page)
  return page
}

export const members = defineFlow<Event>({
  id: 'members',
  title: 'People and invitations',
  source:
    'frontend/src/pages/People.vue, frontend/src/pages/PersonProfile.vue, frontend/src/components/Settings/MembersSettings.vue, frontend/src/components/Settings/InvitePeople.vue, gameplan/api.py (accept_invitation)',
  machine,
  async enter(scene) {
    holds.set(scene, await scene.hold(PEOPLE_URL))
    await scene.goto('/people')
    await expect(scene.page.getByText('0 members')).toBeVisible({ timeout: 20_000 })
  },
  events: {
    async LOADS(scene) {
      await holds.get(scene)?.release()
      await expect(scene.page.getByText('Priya Sharma').first()).toBeVisible()
      await expect(scene.page.getByText(/^[1-9]\d* members$/)).toBeVisible()
    },
    async FAILS(scene) {
      await holds.get(scene)?.abort(500)
      await expect(scene.page.getByText('Internal Server Error')).toBeVisible({ timeout: 30_000 })
    },
    async SEARCH_MISS(scene) {
      await scene.page.getByPlaceholder('Search', { exact: true }).first().fill('Zoltan')
      await expect(scene.page.getByText('No members match your search')).toBeVisible()
    },
    async OPEN_PROFILE(scene) {
      await scene.page.getByText('Priya Sharma').first().click()
      await expect(scene.page).toHaveURL(/\/people\/priya/)
      await expect(scene.page.getByRole('radio', { name: 'Posts' })).toBeVisible()
      await expect(scene.page.locator('.animate-pulse')).toHaveCount(0)
      await scene.page.mouse.move(700, 20)
    },
    async OPEN_MISSING_PROFILE(scene) {
      await scene.goto('/people/ruth@moonhollow.studio')
      await expect(scene.page.getByText(/not found/i).first()).toBeVisible({ timeout: 20_000 })
    },
    async MANAGE_USERS(scene) {
      await scene.page.getByRole('button', { name: 'Invite' }).first().click()
      await expect(scene.page).toHaveURL(/\/settings\/users$/)
      await expect(settingsDialog(scene).getByText('Priya Sharma')).toBeVisible({ timeout: 20_000 })
      await scene.page.mouse.move(700, 20)
    },
    async PICK_ADMIN_ROLE(scene) {
      // The innermost element holding both Priya's email and a role picker is her row.
      const row = settingsDialog(scene)
        .locator('div')
        .filter({ has: scene.page.getByText('priya@moonhollow.studio') })
        .filter({ has: scene.page.getByRole('combobox') })
        .last()
      await row.getByRole('combobox').click()
      await scene.page.getByRole('option', { name: 'Admin' }).click()
      await expect(scene.page.getByRole('dialog').filter({ hasText: 'Change Role' })).toBeVisible()
      await scene.page.mouse.move(700, 20)
    },
    async OPEN_INVITE(scene) {
      await settingsDialog(scene).getByRole('button', { name: 'Invite' }).click()
      await expect(inviteDialog(scene).getByLabel('Invite by email')).toBeVisible()
      await scene.page.mouse.move(700, 20)
    },
    async TYPE_EMAILS(scene) {
      await inviteDialog(scene).getByLabel('Invite by email').fill(INVITEES.join(', '))
      await expect(inviteDialog(scene).getByRole('button', { name: 'Invite' })).toBeVisible()
    },
    async SEND(scene) {
      holds.set(scene, await scene.hold(INVITE_URL))
      await inviteDialog(scene).getByRole('button', { name: 'Invite' }).click()
      await expect(inviteDialog(scene).getByLabel('Invite by email')).toBeDisabled()
      await scene.page.mouse.move(700, 20)
    },
    async SENT(scene) {
      await holds.get(scene)?.release()
      await expect(inviteDialog(scene).getByText('2 invitations sent')).toBeVisible({ timeout: 20_000 })
      await expect(inviteDialog(scene).getByText('Pending Invites')).toBeVisible()
    },
    async SEND_FAILS(scene) {
      await holds.get(scene)?.abort(500)
      await expect(inviteDialog(scene).getByText('Internal Server Error')).toBeVisible({ timeout: 30_000 })
    },
    async INVITEE_OPENS_LINK(scene) {
      // The sent email's key exists only in the mail, so mint Nadia a link of her own.
      const { key } = await scene.call<{ key: string }>(scene.admin, 'gameplan.ui_test_helpers.create_invitation', {
        email: INVITEES[0],
        role: 'Gameplan Member',
      })
      const page = await visitor(scene)
      await page.goto(`/api/method/gameplan.api.accept_invitation?key=${key}`)
      await expect(page).toHaveURL(/update-password/)
      await expect(page.getByRole('button').first()).toBeVisible()
    },
    async INVITEE_OPENS_BROKEN_LINK(scene) {
      const page = await visitor(scene)
      await page.goto('/api/method/gameplan.api.accept_invitation?key=4f1c9e2a7b')
      await expect(page.getByText('This invitation link is no longer valid').first()).toBeVisible()
    },
  },
  frame(scene, state) {
    if (state !== 'setPassword' && state !== 'linkInvalid') return null
    return visitors.get(scene)?.locator('html') ?? null
  },
})
