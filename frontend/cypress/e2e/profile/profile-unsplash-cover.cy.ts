import { personas } from '../../support/personas'
import { resetData } from '../../support/seed'

// The cover image can come from Unsplash instead of a file. Every request goes
// through our own proxy (`gameplan.unsplash.search_photos`), which is what these
// specs stub — CI must never call api.unsplash.com, and a site with no access
// key configured would answer "not configured" to every one of them anyway.
//
// The picker only chooses. What it must prove is that the chosen photo lands on
// the profile through the same write path an upload uses, that Unsplash's
// download ping is fired on the pick and not on the search, and that every way
// the proxy can fail says something a person can act on.

const searchUrl = '**/api/v2/method/gameplan.unsplash.search_photos*'
const trackUrl = '**/api/v2/method/gameplan.unsplash.track_download'

const photoUrl = 'https://images.unsplash.com/photo-abc123?w=1080'
const downloadLocation = 'https://api.unsplash.com/photos/abc123/download?ixid=xyz'

const photo = {
  id: 'abc123',
  thumb_url: '/assets/frappe/images/background.png',
  url: photoUrl,
  alt: 'a desk by a window',
  photographer_name: 'A Photographer',
  photographer_url: 'https://unsplash.com/@aphotographer?utm_source=gameplan&utm_medium=referral',
  photo_url: 'https://unsplash.com/photos/abc123?utm_source=gameplan&utm_medium=referral',
  download_location: downloadLocation,
}

describe('Profile cover image from Unsplash', () => {
  let memberProfile: string

  beforeEach(() => {
    // The editor aside, which holds the cover controls, only exists from `md` up.
    cy.viewport(1280, 1000)
    resetData('space_with_discussion')
    // Still Administrator here, who may write every profile.
    profileNameFor(personas.member.email).then((name) => {
      memberProfile = name
      // Both bound image fields need a value: a bound card whose field is empty
      // is not rendered at all, and the avatar card has to exist for the
      // "cover only" rule to be provable rather than vacuous.
      setProfileFields(name, {
        cover_image: '/assets/frappe/images/background.png',
        image: '/assets/frappe/images/default-avatar.png',
      })
    })
  })

  it('sets the cover to the chosen photo, and reports the download to Unsplash', () => {
    stubSearch({ configured: true, query: 'desk', total: 1, photos: [photo] })
    cy.intercept('POST', trackUrl, { body: { data: { configured: true, tracked: true } } }).as(
      'track',
    )
    cy.intercept('PUT', '**/api/v2/document/GP%20User%20Profile/*').as('saveProfile')

    openPicker()
    // Opening browses the default topic, so there is something to look at before
    // anything is typed.
    cy.wait('@search').its('request.query').should('deep.include', { query: '', topic: 'featured' })

    searchInput().type('desk')
    cy.wait('@search').its('request.query').should('deep.include', { query: 'desk', topic: '' })

    // Attribution is on screen before anything is picked, as Unsplash requires.
    cy.contains('a', 'A Photographer')
      .should('have.attr', 'href')
      .and('include', 'utm_source=gameplan')

    // Nothing is reported as a download merely for being shown.
    cy.get('@track.all').should('have.length', 0)

    photoTile('abc123').click()

    cy.wait('@saveProfile').its('request.body.cover_image').should('equal', photoUrl)
    cy.wait('@track').its('request.body.download_location').should('equal', downloadLocation)

    // The remote URL is stored as-is: nothing re-hosts the image.
    profileField(memberProfile, 'cover_image').should('equal', photoUrl)
    cy.get('[data-unsplash-picker]').should('not.exist')
    card('cover').find('img').should('have.attr', 'src', photoUrl)
  })

  it('explains an unconfigured site instead of showing an empty grid', () => {
    stubSearch({
      configured: false,
      message: 'Unsplash is not set up on this site. Add an Unsplash access key.',
      photos: [],
      total: 0,
    })

    openPicker()
    cy.wait('@search')

    cy.get('[data-unsplash-not-configured]').should('contain.text', 'Unsplash is not set up')
    cy.get('[data-unsplash-results]').should('not.exist')
  })

  it('browses a topic, and typing takes over from the chips', () => {
    stubSearch({ configured: true, topic: 'featured', total: 1, photos: [photo] })

    openPicker()
    cy.wait('@search')

    topicChip('nature').click()
    cy.wait('@search').its('request.query').should('deep.include', { query: '', topic: 'nature' })

    // Typing is the more specific intent, so the chip lets go of the results.
    searchInput().type('desk')
    cy.wait('@search').its('request.query').should('deep.include', { query: 'desk', topic: '' })

    // And a chip takes it back, emptying the box on the way.
    topicChip('travel').click()
    cy.wait('@search').its('request.query').should('deep.include', { query: '', topic: 'travel' })
    searchInput().should('have.value', '')

    // The box going empty must not bounce the selection back to the default.
    cy.wait(600)
    cy.get('@search.all').should('have.length', 4)
  })

  it('says so when nothing matches', () => {
    stubSearch({ configured: true, query: 'zzzz', total: 0, photos: [] })

    openPicker()
    cy.wait('@search')
    searchInput().type('zzzz')
    cy.wait('@search')

    cy.get('[data-unsplash-empty]').should('contain.text', 'No photos found')
  })

  it('surfaces an upstream failure as a readable message', () => {
    cy.intercept('GET', searchUrl, {
      statusCode: 500,
      body: { exception: 'frappe.exceptions.ValidationError', _server_messages: '[]' },
      headers: { 'x-frappe-error': "Unsplash's hourly rate limit is used up. Try again later." },
    }).as('search')

    openPicker()
    cy.wait('@search')

    cy.get('[data-unsplash-error]').should('be.visible')
    cy.get('[data-unsplash-results]').should('not.exist')
  })

  it('offers Unsplash for the cover but not for the avatar', () => {
    stubSearch({ configured: true, query: '', total: 0, photos: [] })

    cy.loginAs('member')
    visitCustomize()

    card('cover').click()
    unsplashButton().should('exist')

    card('avatar').click()
    unsplashButton().should('not.exist')
  })
})

function stubSearch(body: Record<string, unknown>) {
  return cy.intercept('GET', searchUrl, { body: { data: body } }).as('search')
}

/** Log in, open the customize editor, select the cover card and open the picker. */
function openPicker() {
  cy.loginAs('member')
  visitCustomize()
  card('cover').click()
  unsplashButton().click()
  return cy.get('[data-unsplash-picker]').should('be.visible')
}

function visitCustomize() {
  cy.visit('/g/profile/customize')
  // The panel and the grid both mount once the bento call resolves.
  return cy.get('[data-profile-info-checklist]').should('be.visible')
}

function unsplashButton() {
  return cy.get('button[data-profile-unsplash-open]')
}

function searchInput() {
  return cy.get('[data-unsplash-search]')
}

function topicChip(slug: string) {
  return cy.get(`button[data-unsplash-topic="${slug}"]`)
}

function photoTile(id: string) {
  return cy.get(`button[data-unsplash-photo="${id}"]`)
}

function card(cardId: string) {
  return cy.get(`article[data-profile-card-id="${cardId}"]`)
}

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
