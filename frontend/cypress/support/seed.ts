// Seed helper for the backend reset API (gameplan.ui_test_helpers.reset).
// Imported per-spec (not globally) so specs opt in to the new seeding flow.

export type Scenario =
  | 'onboarded'
  | 'space_with_discussion'
  | 'private_space_with_guest'
  | 'two_communities'

export interface SeedIds {
  community?: string
  space?: string
  private_space?: string
  discussion?: string
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
