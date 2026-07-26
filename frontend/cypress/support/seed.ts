// Seed helper for the backend reset API (gameplan.ui_test_helpers.reset).
// Imported per-spec (not globally) so specs opt in to the new seeding flow.

export type Scenario =
  | 'onboarded'
  | 'space_with_discussion'
  | 'private_space_with_guest'
  | 'search_page'
  | 'two_communities'
  | 'unread_discussion'

export interface SeedIds {
  community?: string
  space?: string
  /** The empty auto-created General space, when the scenario's `space` is a named one. */
  general_space?: string
  second_space?: string
  private_space?: string
  discussion?: string
  discussion_slug?: string
  public_discussion?: string
  communities?: string[]
  spaces?: string[]
}

/**
 * Reset all Gameplan data and optionally seed a named scenario.
 *
 * One call replaces the old login + clear_data + insert_many seeding dance:
 * it logs in as Administrator, wipes ALL Gameplan data, resets the persona
 * users, and seeds the requested scenario. The returned ids let a spec target
 * the seeded records, and `cy.loginAs` switches to the persona under test.
 *
 * @example
 * resetData('space_with_discussion').then(({ space, discussion }) => {
 *   // ... use space and discussion ids
 * })
 * cy.loginAs('member')
 *
 * @param scenario - Optional scenario name to seed after the reset
 */
export function resetData(scenario?: Scenario): Cypress.Chainable<SeedIds> {
  cy.login()
  return cy
    .request({
      method: 'POST',
      url: '/api/method/gameplan.ui_test_helpers.reset',
      body: { scenario },
    })
    .then((response) => response.body.message as SeedIds)
}

export interface Invitation {
  name: string
  email: string
  key: string
}

/**
 * Mint a pending invitation and return its key, so a spec can drive the
 * accept journey without going through the admin invite UI first.
 *
 * Requires an Administrator session (call after `resetData`, before switching
 * personas with `cy.loginAs`).
 */
export function createInvitation(
  email: string,
  role = 'Gameplan Member',
): Cypress.Chainable<Invitation> {
  cy.login()
  return cy
    .request({
      method: 'POST',
      url: '/api/method/gameplan.ui_test_helpers.create_invitation',
      body: { email, role },
    })
    .then((response) => response.body.message as Invitation)
}
