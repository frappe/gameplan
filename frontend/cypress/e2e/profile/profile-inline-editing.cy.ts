import { personas } from '../../support/personas'
import { resetData } from '../../support/seed'

// A bound card shows a live profile field, and its owner edits that field from
// the card itself. Every write lands on the profile (or User) document, never on
// the bento layout, so `layout_customized` must stay 0: flipping it would opt the
// user out of every future change to the default layout.

const coverImage = '/assets/frappe/images/background.png'
const avatarImage = '/assets/frappe/images/default-avatar.png'

describe('Profile inline editing', () => {
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

  it('saves a bio edited on the card and leaves the layout uncustomized', () => {
    cy.loginAs('member')
    visitProfile(memberProfile)

    cy.intercept('PUT', '**/api/v2/document/GP%20User%20Profile/*').as('saveProfile')
    editTrigger('bio').click()
    card('bio').find('textarea').clear().type('Now writing docs before code.').blur()

    cy.wait('@saveProfile').its('request.body.bio').should('equal', 'Now writing docs before code.')
    card('bio').should('contain.text', 'Now writing docs before code.')
    card('bio').find('textarea').should('not.exist')
    layoutCustomized(memberProfile).should('equal', 0)
  })

  it('saves a name edited on the card through the User doc', () => {
    cy.loginAs('member')
    visitProfile(memberProfile)

    cy.intercept('PUT', '**/api/v2/document/User/*').as('saveUser')
    editTrigger('full-name').click()
    card('full-name').find('input').first().clear().type('Renamed')
    card('full-name').find('input').last().clear().type('Member{ctrl+enter}')

    cy.wait('@saveUser').then(({ request }) => {
      expect(request.body.first_name).to.equal('Renamed')
      expect(request.body.last_name).to.equal('Member')
    })
    card('full-name').should('contain.text', 'Renamed Member')
    layoutCustomized(memberProfile).should('equal', 0)
  })

  it('keeps the stored value when an edit is cancelled with Escape', () => {
    cy.loginAs('member')
    visitProfile(memberProfile)

    editTrigger('bio').click()
    card('bio').find('textarea').clear().type('Never mind{esc}')

    card('bio').find('textarea').should('not.exist')
    card('bio').should('contain.text', 'Async first, with written decisions.')
    card('bio').should('not.contain.text', 'Never mind')
  })

  it('saves the About card through its inline editor', () => {
    cy.loginAs('member')
    visitProfile(memberProfile)

    cy.intercept('PUT', '**/api/v2/document/GP%20User%20Profile/*').as('saveProfile')
    hoverControl('about', 'button[aria-label="Edit About"]').click({ force: true })
    card('about').find('[contenteditable=true]').should('be.visible').click().type(' And the rest.')
    card('about').button('Save').click()

    cy.wait('@saveProfile').its('request.body.readme').should('contain', 'And the rest.')
    card('about').should('contain.text', 'And the rest.')
    layoutCustomized(memberProfile).should('equal', 0)
  })

  it('repositions the cover without customizing the layout', () => {
    cy.loginAs('member')
    visitProfile(memberProfile)

    cy.intercept('POST', '**/method/set_cover_image_position').as('setCoverPosition')
    hoverControl('cover', 'button').contains('Reposition').click({ force: true })
    card('cover').button('Save').click()

    cy.wait('@setCoverPosition').its('response.statusCode').should('equal', 200)
    layoutCustomized(memberProfile).should('equal', 0)
    // Saved without dragging, so the seeded position round-trips unchanged.
    coverImagePosition(memberProfile).should('equal', 30)
  })

  it('shows no editing affordance to a visitor', () => {
    cy.loginAs('secondMember')
    visitProfile(memberProfile)

    cy.get('[data-profile-field-edit-trigger]').should('not.exist')
    cy.get('article[data-profile-card-id] button[aria-label^="Edit "]').should('not.exist')
    cy.get('article[data-profile-card-id] button[aria-label="Change image"]').should('not.exist')
    cy.contains('article[data-profile-card-id] button', 'Reposition').should('not.exist')
    cy.contains('article[data-profile-card-id] button', 'Change').should('not.exist')
    card('bio').should('contain.text', 'Async first, with written decisions.')
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

function profileField(profile: string, fieldname: string) {
  return cy
    .request({
      url: '/api/v2/document/GP User Profile',
      qs: {
        filters: JSON.stringify([['name', '=', profile]]),
        fields: JSON.stringify([fieldname]),
      },
    })
    .then(({ body }) => body.data[0][fieldname])
}

function layoutCustomized(profile: string) {
  return profileField(profile, 'layout_customized')
}

function coverImagePosition(profile: string) {
  return profileField(profile, 'cover_image_position')
}

function visitProfile(profile: string) {
  cy.visit(`/g/people/${profile}`)
  // The grid only mounts once the bento call resolves; the skeleton has no cards.
  return cy.get('article[data-profile-card-id]').should('exist')
}

function card(cardId: string) {
  return cy.get(`article[data-profile-card-id="${cardId}"]`)
}

function editTrigger(cardId: string) {
  return card(cardId).find('[data-profile-field-edit-trigger]')
}

/**
 * A control that only fades in when the card is hovered. Cypress counts
 * `opacity: 0` as hidden and cannot produce a real CSS `:hover`, so these are
 * matched without `:visible` and have to be clicked with `force`.
 */
function hoverControl(cardId: string, selector: string) {
  return card(cardId).find(selector)
}
