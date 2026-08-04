import { personas } from '../../support/personas'
import { resetData } from '../../support/seed'

// A bound card shows a live profile field. The profile page never edits one: the
// owner gets an edit button that hands off to wherever that field is owned —
// Settings → Profile, the About dialog, or the customize page for the cover.
// Every write still lands on the profile (or User) document, never on the bento
// layout, so `layout_customized` must stay 0: flipping it would opt the user out
// of every future change to the default layout.

const coverImage = '/assets/frappe/images/background.png'
const avatarImage = '/assets/frappe/images/default-avatar.png'

describe('Profile card editing', () => {
  let memberProfile: string

  beforeEach(() => {
    cy.viewport(1280, 1000)
    resetData('space_with_discussion')
    // Still Administrator here, who may write every profile.
    profileNameFor(personas.member.email).then((name) => {
      memberProfile = name
      setProfileFields(name, {
        bio: 'Async first, with written decisions.',
        readme: '<p>I look after the docs nobody else wants to write.</p>',
        image: avatarImage,
        cover_image: coverImage,
        cover_image_position: '30',
      })
    })
  })

  it('opens Settings → Profile from the bio card', () => {
    cy.loginAs('member')
    visitProfile(memberProfile)

    editButton('bio').click({ force: true })

    cy.location('pathname').should('equal', '/g/settings/profile')
    cy.get('[role="dialog"]').contains('h2', 'Profile').should('be.visible')
    // Settings is an overlay on the profile page's URL, so leaving it puts the
    // owner back on the card they came from rather than on the home route.
    cy.go('back')
    card('bio').should('contain.text', 'Async first, with written decisions.')
  })

  // The header's edit button lives in a breadcrumb suffix slot, which renders
  // inside that crumb's link — a click that follows the link too would navigate
  // straight back off /settings and close the dialog again.
  it('opens Settings → Profile from the page header and keeps the page behind it', () => {
    cy.loginAs('member')
    visitProfile(memberProfile)

    cy.get('header').find('button[aria-label="Edit profile"]').click()

    cy.get('[role="dialog"]').contains('h2', 'Profile').should('be.visible')
    cy.location('pathname').should('equal', '/g/settings/profile')
    // The dialog is an overlay, so the profile keeps rendering its cards behind it.
    card('bio').should('contain.text', 'Async first, with written decisions.')
  })

  it('opens Settings → Profile from the name and avatar cards', () => {
    cy.loginAs('member')
    visitProfile(memberProfile)

    editButton('full-name').click({ force: true })
    cy.location('pathname').should('equal', '/g/settings/profile')

    cy.go('back')
    editButton('avatar').click({ force: true })
    cy.location('pathname').should('equal', '/g/settings/profile')
  })

  it('edits About in a dialog and leaves the layout uncustomized', () => {
    cy.loginAs('member')
    visitProfile(memberProfile)

    cy.intercept('PUT', '**/api/v2/document/GP%20User%20Profile/*').as('saveProfile')
    editButton('about').click({ force: true })

    cy.get('[role="dialog"]').find('[contenteditable=true]').should('be.visible')
    cy.get('[role="dialog"]').find('[contenteditable=true]').click().type(' And the rest.')
    cy.get('[role="dialog"]').contains('button', 'Save').click()

    cy.wait('@saveProfile').its('request.body.readme').should('contain', 'And the rest.')
    cy.get('[role="dialog"]').should('not.exist')
    card('about').should('contain.text', 'And the rest.')
    layoutCustomized(memberProfile).should('equal', 0)
  })

  it('sends the cover card to the customize page with that card selected', () => {
    cy.loginAs('member')
    visitProfile(memberProfile)

    editButton('cover').click({ force: true })

    cy.location('pathname').should('equal', '/g/profile/customize')
    cy.location('search').should('equal', '?field=cover_image')
    // The panel only names a card once it is selected.
    cy.get('aside').should('contain.text', 'Cover image')
    cy.get('aside').contains('button', 'Reposition').should('exist')
  })

  it('shows no editing affordance to a visitor', () => {
    cy.loginAs('secondMember')
    visitProfile(memberProfile)

    cy.get('[data-profile-card-edit]').should('not.exist')
    cy.get('article[data-profile-card-id] button[aria-label^="Edit "]').should('not.exist')
    card('bio').should('contain.text', 'Async first, with written decisions.')
  })

  it('offers no inline editor on a bound card', () => {
    cy.loginAs('member')
    visitProfile(memberProfile)

    card('bio').click()
    card('bio').find('textarea').should('not.exist')
    card('about').find('[contenteditable=true]').should('not.exist')
    cy.contains('article[data-profile-card-id] button', 'Reposition').should('not.exist')
    cy.contains('article[data-profile-card-id] button', 'Change').should('not.exist')
  })
})

/** The `GP User Profile` name, which is also the `:personId` route param. */
function profileNameFor(email: string) {
  return cy
    .request({
      url: '/api/v2/document/GP User Profile',
      qs: {
        filters: JSON.stringify([['user', '=', email]]),
        fields: JSON.stringify(['name']),
      },
    })
    .then(({ body }) => body.data[0].name as string)
}

/** Write profile fields as Administrator, who may edit any profile. */
function setProfileFields(profile: string, values: Record<string, string>) {
  return cy.request({
    method: 'PUT',
    url: `/api/v2/document/GP User Profile/${encodeURIComponent(profile)}`,
    body: values,
  })
}

function layoutCustomized(profile: string) {
  return cy
    .request({
      url: '/api/v2/document/GP User Profile',
      qs: {
        filters: JSON.stringify([['name', '=', profile]]),
        fields: JSON.stringify(['layout_customized']),
      },
    })
    .then(({ body }) => body.data[0].layout_customized)
}

function visitProfile(profile: string) {
  cy.visit(`/g/people/${profile}`)
  // The grid only mounts once the bento call resolves; the skeleton has no cards.
  return cy.get('article[data-profile-card-id]').should('exist')
}

function card(cardId: string) {
  return cy.get(`article[data-profile-card-id="${cardId}"]`)
}

/**
 * The card's edit button only fades in on hover. Cypress counts `opacity: 0` as
 * hidden and cannot produce a real CSS `:hover`, so it is matched without
 * `:visible` and clicked with `force`.
 */
function editButton(cardId: string) {
  return card(cardId).find('[data-profile-card-edit]')
}
