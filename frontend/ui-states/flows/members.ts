import { expect, type Page } from '@playwright/test'
import { setup } from 'xstate'
import { defineFlow, pressEmpty } from '../flow'
import type { Hold, Scene } from '../scene'

type Event =
  | { type: 'LOADS' }
  | { type: 'FAILS' }
  | { type: 'SEARCH_MISS' }
  | { type: 'OPEN_PROFILE' }
  | { type: 'OPEN_MISSING_PROFILE' }
  | { type: 'MANAGE_USERS' }
  | { type: 'PICK_ADMIN_ROLE' }
  | { type: 'HOVER_USER' }
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
          'The People list request is still out: the heading says "Members" with no count, and three skeleton rows sit under the column headers.',
      },
      on: { LOADS: 'directory', FAILS: 'directoryFailed' },
    },
    directoryFailed: {
      meta: {
        description:
          'The People list request failed: "Could not load people." with a Retry button where the rows would be, lined up with the table.',
      },
    },
    directory: {
      meta: {
        description:
          'People: 16 members, Maya first, then by last update, with post, reply and reaction counts. Admins see a solid Invite button.',
      },
      on: {
        SEARCH_MISS: 'searchEmpty',
        OPEN_PROFILE: 'profile',
        OPEN_MISSING_PROFILE: 'profileMissing',
        OPEN_INVITE: 'inviteOpen',
        MANAGE_USERS: 'usersSettings',
      },
    },
    searchEmpty: {
      meta: {
        description:
          'A search that matches nobody: "0 members" and a "No members match your search" box aligned with the table.',
      },
    },
    profile: {
      meta: {
        description:
          "Priya Sharma's profile: Profile, Posts and Replies tabs over her cover, avatar, name and bio cards.",
      },
    },
    profileMissing: {
      meta: {
        description:
          'A profile link for someone who is not here: "Profile not found" inside the app shell, with a People / Not found breadcrumb and a "Go to Home" button.',
      },
    },
    usersSettings: {
      meta: {
        description:
          'Settings › Users, opened from the account menu: everyone with a role picker, the date they joined, and the same solid Invite button as People. The disable button stays hidden until a row is hovered.',
      },
      on: { PICK_ADMIN_ROLE: 'roleConfirm', HOVER_USER: 'userHover' },
    },
    userHover: {
      meta: {
        description:
          "The pointer on Priya Sharma's row in Settings › Users: a ghost disable button appears at the row's right end. Other rows show none.",
      },
    },
    roleConfirm: {
      meta: {
        description:
          'Picking Admin for Priya asks "Change Priya Sharma\'s role to Admin?", with one sentence on what that allows and a "Change role" button.',
      },
    },
    inviteOpen: {
      meta: {
        description:
          'Invite on People opens the "Invite people" dialog in place: an empty email box with its helper line, the Role picker (User) and what it allows, and Cancel beside a disabled Invite. There are no pending invites yet, so that list is absent.',
      },
      on: { TYPE_EMAILS: 'inviteFilled' },
    },
    inviteFilled: {
      meta: {
        description: 'Two addresses typed: Invite becomes enabled.',
      },
      on: { SEND: 'inviteSending' },
    },
    inviteSending: {
      meta: {
        description:
          'Invite was clicked and the request is out: the button spins and the email box, still showing the two addresses, is disabled.',
      },
      on: { SENT: 'inviteSent', SEND_FAILS: 'inviteFailed' },
    },
    inviteSent: {
      meta: {
        description:
          'The invitations went out: the email box empties, a grey box says "2 invitations sent" with the addresses, "Pending invites" lists both, and Cancel becomes Done.',
      },
      on: { INVITEE_OPENS_LINK: 'setPassword', INVITEE_OPENS_BROKEN_LINK: 'linkInvalid' },
    },
    inviteFailed: {
      meta: {
        description:
          'The invite request failed: a red sentence next to Cancel and Invite, and the two addresses stay in the box to try again.',
      },
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
          'An invitation link whose key is wrong, opened signed out: the server sends it to /g/invitation-invalid, a page without the app shell: the Gameplan logo, "This invitation link is no longer valid", "Ask the person who invited you to send a new one." and a "Sign in" button.',
      },
    },
  },
})

const holds = new WeakMap<Scene, Hold>()
/** A browser with no session, for what an invitee sees before they have an account. */
const visitors = new WeakMap<Scene, Page>()

const PEOPLE_URL =
  '**/api/v2/method/gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.get_list*'
const INVITE_URL = '**/api/v2/method/gameplan.api.invite_by_email*'
const INVITEES = ['nadia@moonhollow.studio', 'omar@moonhollow.studio']

function settingsDialog(scene: Scene) {
  return scene.page.getByRole('dialog').first()
}

function inviteDialog(scene: Scene) {
  return scene.page.getByRole('dialog').filter({ hasText: 'Invite people' }).last()
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
    await expect(scene.page.getByLabel('Loading member').first()).toBeVisible({ timeout: 20_000 })
    await expect(
      scene.page.getByText('Members', { exact: true }).filter({ visible: true }),
    ).toBeVisible()
  },
  events: {
    async LOADS(scene) {
      await holds.get(scene)?.release()
      await expect(scene.page.getByText('Priya Sharma').first()).toBeVisible()
      await expect(scene.page.getByText(/^[1-9]\d* members$/)).toBeVisible()
    },
    async FAILS(scene) {
      await holds.get(scene)?.abort(500)
      await expect(scene.page.getByText('Could not load people.')).toBeVisible({ timeout: 30_000 })
      await expect(scene.page.getByRole('button', { name: 'Retry' })).toBeVisible()
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
      await expect(scene.page.getByText('Profile not found')).toBeVisible({ timeout: 20_000 })
      await expect(scene.page.getByRole('link', { name: 'Go to Home' })).toBeVisible()
    },
    async MANAGE_USERS(scene) {
      await pressEmpty(scene.page)
      await scene.page.getByRole('button', { name: /^Account menu/ }).click()
      await scene.page.getByRole('menuitem', { name: /^Settings/ }).click()
      await settingsDialog(scene).getByRole('tab', { name: 'Users' }).click()
      await expect(scene.page).toHaveURL(/\/settings\/users$/)
      await expect(settingsDialog(scene).getByText('Priya Sharma')).toBeVisible({ timeout: 20_000 })
      await scene.page.mouse.move(700, 20)
    },
    async HOVER_USER(scene) {
      const disable = settingsDialog(scene).getByRole('button', { name: 'Disable Priya Sharma' })
      await expect(disable).toHaveCSS('opacity', '0')
      await settingsDialog(scene).getByText('priya@moonhollow.studio').hover()
      await expect(disable).toHaveCSS('opacity', '1')
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
      await expect(
        scene.page.getByRole('dialog').filter({ hasText: "Change Priya Sharma's role to Admin?" }),
      ).toBeVisible()
      await scene.page.mouse.move(700, 20)
    },
    async OPEN_INVITE(scene) {
      await scene.page
        .getByRole('button', { name: 'Invite', exact: true })
        .filter({ visible: true })
        .first()
        .click()
      await expect(scene.page).toHaveURL(/\/people$/)
      await expect(inviteDialog(scene).getByLabel('Invite by email')).toBeVisible()
      await expect(
        inviteDialog(scene).getByRole('button', { name: 'Invite', exact: true }),
      ).toBeDisabled()
      await scene.page.mouse.move(700, 20)
    },
    async TYPE_EMAILS(scene) {
      await inviteDialog(scene).getByLabel('Invite by email').fill(INVITEES.join(', '))
      await expect(
        inviteDialog(scene).getByRole('button', { name: 'Invite', exact: true }),
      ).toBeEnabled()
    },
    async SEND(scene) {
      holds.set(scene, await scene.hold(INVITE_URL))
      await inviteDialog(scene).getByRole('button', { name: 'Invite', exact: true }).click()
      await expect(inviteDialog(scene).getByLabel('Invite by email')).toBeDisabled()
      await scene.page.mouse.move(700, 20)
    },
    async SENT(scene) {
      await holds.get(scene)?.release()
      await expect(inviteDialog(scene).getByText('2 invitations sent')).toBeVisible({
        timeout: 20_000,
      })
      await expect(inviteDialog(scene).getByText('Pending invites')).toBeVisible()
    },
    async SEND_FAILS(scene) {
      await holds.get(scene)?.abort(500)
      await expect(inviteDialog(scene).getByRole('alert')).toBeVisible({ timeout: 30_000 })
      await expect(inviteDialog(scene).getByLabel('Invite by email')).toHaveValue(
        INVITEES.join(', '),
      )
    },
    async INVITEE_OPENS_LINK(scene) {
      // The sent email's key exists only in the mail, so mint Nadia a link of her own.
      const { key } = await scene.call<{ key: string }>(
        scene.admin,
        'gameplan.ui_test_helpers.create_invitation',
        {
          email: INVITEES[0],
          role: 'Gameplan Member',
        },
      )
      const page = await visitor(scene)
      await page.goto(`/api/method/gameplan.api.accept_invitation?key=${key}`)
      await expect(page).toHaveURL(/update-password/)
      await expect(page.getByRole('button').first()).toBeVisible()
    },
    async INVITEE_OPENS_BROKEN_LINK(scene) {
      const page = await visitor(scene)
      await page.goto('/api/method/gameplan.api.accept_invitation?key=4f1c9e2a7b')
      await expect(page).toHaveURL(/\/g\/invitation-invalid/, { timeout: 20_000 })
      await expect(page.getByText('This invitation link is no longer valid')).toBeVisible()
    },
  },
  frame(scene, state) {
    if (state !== 'setPassword' && state !== 'linkInvalid') return null
    return visitors.get(scene)?.locator('html') ?? null
  },
})
