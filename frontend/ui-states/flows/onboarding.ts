import { expect, type Locator } from '@playwright/test'
import { setup } from 'xstate'
import { defineFlow } from '../flow'
import { testPeople, type Hold, type Scene } from '../scene'

type Event =
  | { type: 'FILL' }
  | { type: 'MISTYPE_EMAIL' }
  | { type: 'SUBMIT' }
  | { type: 'SUCCEEDS' }
  | { type: 'FAILS' }
  | { type: 'SUBMIT_AFTER_SETUP_ELSEWHERE' }
  | { type: 'COMMUNITY_CREATED_ELSEWHERE' }
  | { type: 'ADMIN_VISITS' }
  | { type: 'COMMUNITY_MADE_PRIVATE' }

/**
 * A site with no communities, and a person who has joined none.
 *
 * The router decides between the two pages in `getDesktopHomeRoute`
 * (`frontend/src/router.ts`) from the communities and spaces the person can
 * see, not from their role: an empty list sends anyone to Onboarding, a list
 * with nothing joined sends them to NoCommunities. Every path starts as
 * `testPeople.member`, a Gameplan Member, on a site `seed()` has emptied.
 */
const machine = setup({ types: { events: {} as Event } }).createMachine({
  id: 'onboarding',
  initial: 'blank',
  states: {
    blank: {
      meta: {
        description:
          'An empty site, opened by a Gameplan Member: "Welcome to Gameplan" with three empty steps beside a preview of the rail and sidebar (General and "Your first space"). The space icon button shows a smile-plus, and Continue is disabled.',
      },
      on: { FILL: 'filled', COMMUNITY_CREATED_ELSEWHERE: 'notJoined' },
    },
    filled: {
      meta: {
        description:
          'Community "Moonhollow Studios", first space "Engineering" and two teammates typed in. The preview rail and sidebar show the names as they are typed.',
      },
      on: {
        MISTYPE_EMAIL: 'badEmail',
        SUBMIT: 'submitting',
        SUBMIT_AFTER_SETUP_ELSEWHERE: 'alreadySetUp',
      },
    },
    badEmail: {
      meta: {
        description:
          'One address is missing its domain. Leaving the field shows "omar@moonhollow is not a valid email address" under it, and Continue sends nothing until it is fixed.',
      },
    },
    submitting: {
      meta: { description: 'Continue was clicked and the setup request is out: the button spins, the fields stay editable.' },
      on: { SUCCEEDS: 'done', FAILS: 'failed' },
    },
    failed: {
      meta: {
        description:
          'The setup request failed: "Could not set up Gameplan. Try again." in red beside Continue, and the form kept as typed so Continue can be tried again.',
      },
    },
    done: {
      meta: { description: "Setup finished: the new community's feed, with Engineering and General in the sidebar, the All discussions / Participating / Unread tabs, and a \"No discussions yet\" box." },
    },
    alreadySetUp: {
      meta: {
        description:
          'Someone else created a community while this form was open. Continue fails with "This site is already set up." in red beside it, and the page offers no way out but a reload.',
      },
    },
    notJoined: {
      meta: {
        description:
          'An admin created a public community the member is not in. Home is now "You have not joined a community" with a Browse communities button.',
      },
      on: { ADMIN_VISITS: 'notJoinedAdmin', COMMUNITY_MADE_PRIVATE: 'privateOnly' },
    },
    notJoinedAdmin: {
      meta: {
        description:
          'The same page for Administrator after leaving the community they created: the button reads Manage communities instead.',
      },
    },
    privateOnly: {
      meta: {
        description:
          'The only community turned private. The member can see no community or space, so the router sends them back to an empty Onboarding form, which can only end in "This site is already set up".',
      },
    },
  },
})

const holds = new WeakMap<Scene, Hold>()

const ONBOARDING_URL = '**/api/v2/method/gameplan.api.onboarding*'
const COMMUNITY = 'Moonhollow Studios'
const SPACE = 'Engineering'

function continueButton(scene: Scene) {
  return scene.page.getByRole('button', { name: 'Continue' })
}

function emailsField(scene: Scene) {
  return scene.page.getByPlaceholder('jane@example.com, sam@example.com')
}

/** Opens a path and waits for `ready`, the element only the target screen has. */
async function open(scene: Scene, path: string, ready: Locator): Promise<void> {
  await scene.goto(path)
  await expect(ready.first()).toBeVisible({ timeout: 20_000 })
}

/**
 * A community made by someone else while this page is open. Felix runs it
 * with Administrator, so Administrator can leave it again.
 */
async function createCommunityElsewhere(scene: Scene): Promise<void> {
  await scene.insert(scene.admin, 'GP Team', {
    title: COMMUNITY,
    members: [{ user: testPeople.member2.email, is_admin: 1 }],
  })
}

export const onboarding = defineFlow<Event>({
  id: 'onboarding',
  title: 'Onboarding and no communities',
  source: 'frontend/src/pages/Onboarding.vue, frontend/src/pages/NoCommunities.vue, frontend/src/router.ts (getDesktopHomeRoute)',
  machine,
  async enter(scene) {
    await scene.seed()
    await open(scene, '/', scene.page.getByText('Welcome to Gameplan'))
    await expect(continueButton(scene)).toBeDisabled()
  },
  events: {
    async FILL(scene) {
      await scene.page.locator('#new-community-name').fill(COMMUNITY)
      await scene.page.locator('#new-space-name').fill(SPACE)
      await emailsField(scene).fill('nadia@moonhollow.studio, omar@moonhollow.studio')
      await expect(continueButton(scene)).toBeEnabled()
      await expect(scene.page.getByText(SPACE, { exact: true }).first()).toBeVisible()
    },
    async MISTYPE_EMAIL(scene) {
      await emailsField(scene).fill('nadia@moonhollow.studio, omar@moonhollow')
      await emailsField(scene).blur()
      await expect(scene.page.getByText('omar@moonhollow is not a valid email address')).toBeVisible()
    },
    async SUBMIT(scene) {
      holds.set(scene, await scene.hold(ONBOARDING_URL))
      await continueButton(scene).click()
      await expect(continueButton(scene)).toBeDisabled()
      await scene.page.mouse.move(700, 20)
    },
    async SUCCEEDS(scene) {
      await holds.get(scene)?.release()
      await expect(scene.page).toHaveURL(/\/community\/[^/]+\/discussions/, { timeout: 40_000 })
      await expect(scene.page.getByText(SPACE, { exact: true }).first()).toBeVisible()
    },
    async FAILS(scene) {
      await holds.get(scene)?.abort(500)
      await expect(continueButton(scene)).toBeEnabled({ timeout: 30_000 })
      await expect(scene.page.getByText(/Could not set up Gameplan|Something went wrong/)).toBeVisible()
    },
    async SUBMIT_AFTER_SETUP_ELSEWHERE(scene) {
      await createCommunityElsewhere(scene)
      await continueButton(scene).click()
      await expect(scene.page.getByText('This site is already set up')).toBeVisible({ timeout: 30_000 })
      await scene.page.mouse.move(700, 20)
    },
    async COMMUNITY_CREATED_ELSEWHERE(scene) {
      await createCommunityElsewhere(scene)
      await open(scene, '/', scene.page.getByText('You have not joined a community'))
    },
    async ADMIN_VISITS(scene) {
      // Administrator created the community, which made them a member; leave it first.
      const team = await scene.find('GP Team', { title: COMMUNITY })
      await scene.method(scene.admin, 'GP Team', team, 'remove_member', { user: scene.people.admin.email })
      await scene.signIn(scene.people.admin)
      await open(scene, '/', scene.page.getByRole('button', { name: 'Manage communities' }))
    },
    async COMMUNITY_MADE_PRIVATE(scene) {
      const team = await scene.find('GP Team', { title: COMMUNITY })
      const response = await scene.admin.put(`/api/resource/GP%20Team/${encodeURIComponent(team)}`, {
        data: { is_private: 1 },
      })
      if (!response.ok()) throw new Error(`Making ${COMMUNITY} private failed: ${response.status()}`)
      await open(scene, '/', scene.page.getByText('Welcome to Gameplan'))
    },
  },
})
