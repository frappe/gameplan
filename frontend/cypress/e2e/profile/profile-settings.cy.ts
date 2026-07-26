import { resetData } from '../../support/seed'

// One settings journey: a member updates their identity, publishes one profile
// card, and replaces a quick reaction that then appears in the discussion picker.
// Permission boundaries and malformed settings live in test_profiles.py.
describe('Profile settings', () => {
  let community: string
  let space: string
  let discussion: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      discussion = String(ids.discussion)
    })
    cy.loginAs('member')
  })

  it('edits the profile, adds a bento card, and sets quick reactions', () => {
    cy.intercept('PUT', '**/api/v2/document/User/*').as('saveName')
    cy.intercept('PUT', '**/api/v2/document/GP%20User%20Profile/*').as('saveBio')
    cy.visit('/g/settings/profile')
    cy.get('[role="dialog"]').contains('h2', 'Profile').should('be.visible')

    labelledInput('First name').clear().type('Maya').blur()
    cy.wait('@saveName').its('request.body.first_name').should('equal', 'Maya')
    cy.contains('Name saved').should('exist')
    labelledTextarea('Bio').type('Building calm tools for remote teams.').blur()
    cy.wait('@saveBio')
      .its('request.body.bio')
      .should('equal', 'Building calm tools for remote teams.')

    cy.intercept(
      'POST',
      '**/gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.get_my_bento_cards',
    ).as('getBentoCards')
    cy.get('[role="dialog"]').contains('button', 'Customize').click()
    cy.wait('@getBentoCards')

    cy.button('Start with basics').click()
    cy.get('header').contains('button', 'Card').click()
    labelledInput('Title').clear().type('How I work')
    labelledTextarea('Text').clear().type('Async first, with written decisions.')

    cy.intercept(
      'POST',
      '**/gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.save_my_bento_cards',
    ).as('saveBentoCards')
    cy.get('header').contains('button', 'Save').click()
    cy.wait('@saveBentoCards').then(({ request }) => {
      expect(request.body.cards).to.deep.include({
        id: request.body.cards.at(-1).id,
        type: 'Card',
        size: '2x1',
        title: 'How I work',
        text: 'Async first, with written decisions.',
        imageRendering: 'Cover',
        imagePosition: 50,
      })
    })
    cy.contains('Profile layout saved').should('be.visible')

    cy.get('header')
      .contains('a', /^Maya(?:\s|$)/)
      .click()
    cy.contains('How I work').should('be.visible')
    cy.contains('Async first, with written decisions.').should('be.visible')

    cy.visit('/g/settings/preferences')
    cy.get('[role="dialog"]').contains('h2', 'Preferences').should('be.visible')
    cy.intercept('PUT', '**/api/v2/document/GP%20User%20Profile/*').as('saveQuickReactions')
    cy.get('[role="dialog"]').contains('button', '👍').click()
    cy.get('input[placeholder="Search by keyword"]:visible').type('grinning face')
    cy.get('button[title="grinning face"]:visible').click()
    cy.wait('@saveQuickReactions').then(({ request }) => {
      expect(JSON.parse(request.body.quick_reaction_emojis)[0]).to.equal('😀')
    })

    cy.reload()
    cy.get('[role="dialog"]').contains('h2', 'Preferences').should('be.visible')
    cy.get('[role="dialog"]').contains('button', '😀').scrollIntoView().should('be.visible')

    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}`)
    cy.get('button[aria-label="Add a reaction"]').click()
    cy.get('button:contains("😀"):visible').should('exist')
    cy.get('button:contains("👍"):visible').should('not.exist')
  })
})

function labelledInput(label: string) {
  return cy.contains('label', label).then(($label) => cy.get(`input[id="${$label.attr('for')}"]`))
}

function labelledTextarea(label: string) {
  return cy
    .contains('label', label)
    .then(($label) => cy.get(`textarea[id="${$label.attr('for')}"]`))
}
