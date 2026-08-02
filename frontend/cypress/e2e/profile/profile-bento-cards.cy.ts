import { personas } from '../../support/personas'
import { resetData } from '../../support/seed'

// The profile page renders a computed default layout of *bound* cards: each one
// resolves its value from the profile on read instead of storing a copy. A bound
// card whose field is empty is not rendered at all, and the page looks the same
// for the owner and for a visitor.
//
// Permission rules, the save-path validation and the empty-value matrix live in
// test_profiles.py. This spec walks the page a person actually sees.

const boundCardSizes: Record<string, string> = {
  cover: '4x1',
  avatar: '1x1',
  'full-name': '1x1',
  bio: '2x1',
  about: '4x2',
}

const defaultCardOrder = ['cover', 'avatar', 'full-name', 'bio', 'about']

// Real images served by the bench, so the card renders an <img> that actually loads.
const coverImage = '/assets/frappe/images/background.png'
const avatarImage = '/assets/frappe/images/default-avatar.png'

// Long enough to overflow the 4x2 About tile, so "Read more" appears.
const longReadme = Array.from(
  { length: 30 },
  (_, index) =>
    `<p>About paragraph ${index + 1}. Written decisions beat meetings, so this section keeps ` +
    `going long past the height of the card that holds it.</p>`,
).join('')

const bentoMethod = 'gameplan.gameplan.doctype.gp_user_profile.gp_user_profile'

describe('Profile bento cards', () => {
  let memberProfile: string
  let outsiderProfile: string

  beforeEach(() => {
    cy.viewport(1280, 900)
    resetData('space_with_discussion')
    // Still Administrator here, who may read and write every profile.
    profileNameFor(personas.member.email).then((name) => (memberProfile = name))
    profileNameFor(personas.outsider.email).then((name) => (outsiderProfile = name))
  })

  it('shows every bound card, in order, at its default size', () => {
    setProfileFields(memberProfile, {
      bio: 'Async first, with written decisions.',
      readme: '<p>I look after the docs nobody else wants to write.</p>',
      image: avatarImage,
      cover_image: coverImage,
    })

    cy.loginAs('secondMember')
    visitProfile(memberProfile)

    cy.get('article[data-profile-card-id]').should('have.length', defaultCardOrder.length)
    cardIdsInOrder().should('deep.equal', defaultCardOrder)
    for (const cardId of defaultCardOrder) {
      card(cardId).should('have.attr', 'data-size', boundCardSizes[cardId])
    }

    card('cover').find('img').should('have.attr', 'src', coverImage)
    card('avatar').find('img').should('have.attr', 'src', avatarImage)
    card('full-name').should('contain.text', personas.member.displayName)
    card('bio').should('contain.text', 'Async first, with written decisions.')
    card('about').should('contain.text', 'I look after the docs nobody else wants to write.')
  })

  it('renders nothing but the name card when the profile is empty', () => {
    // `outsider` is seeded with a name and nothing else, so every other bound
    // field is empty and its card must be dropped rather than placeheld.
    cy.loginAs('secondMember')
    visitProfile(outsiderProfile)
    assertOnlyNameCard()

    // Identical for the owner: no "add your bio" affordance in place of a card.
    cy.switchUser('outsider')
    visitProfile(outsiderProfile)
    assertOnlyNameCard()
  })

  it('shows the new bio after the bio is edited', () => {
    setProfileFields(memberProfile, { bio: 'Async first, with written decisions.' })

    cy.loginAs('member')
    // Persist the computed default as stored rows. Frozen copies only ever
    // existed on a saved layout, so this is the path the bug lived on.
    cy.request('POST', `/api/method/${bentoMethod}.get_my_bento_cards`)
      .then(({ body }) =>
        cy.request('POST', `/api/method/${bentoMethod}.save_my_bento_cards`, {
          cards: body.message.cards,
        }),
      )
      .then(({ body }) => {
        expect(body.message.is_default, 'layout is stored, not computed').to.equal(false)
      })

    visitProfile(memberProfile)
    card('bio').should('contain.text', 'Async first, with written decisions.')

    cy.intercept('PUT', '**/api/v2/document/GP%20User%20Profile/*').as('saveProfile')
    cy.visit('/g/settings/profile')
    cy.get('[role="dialog"]').contains('h2', 'Profile').should('be.visible')
    labelledTextarea('Bio').clear().type('Now writing docs before code.').blur()
    cy.wait('@saveProfile').its('request.body.bio').should('equal', 'Now writing docs before code.')

    visitProfile(memberProfile)
    card('bio').should('contain.text', 'Now writing docs before code.')
    card('bio').should('not.contain.text', 'Async first, with written decisions.')
  })

  it('redirects the old About tab to the profile page', () => {
    cy.loginAs('secondMember')
    cy.visit(`/g/people/${memberProfile}/about`)

    cy.location('pathname').should('equal', `/g/people/${memberProfile}`)
    cy.contains('button', 'Profile').should('be.visible')
    cy.contains('button', 'Posts').should('be.visible')
    cy.contains('button', 'Replies').should('be.visible')
    cy.contains('button', 'About').should('not.exist')
  })

  it('expands and collapses a long About card without moving the cards above it', () => {
    setProfileFields(memberProfile, {
      bio: 'Async first, with written decisions.',
      readme: longReadme,
      image: avatarImage,
      cover_image: coverImage,
    })

    // Tall enough that the whole collapsed grid fits without scrolling: Cypress
    // reports an element outside the app's scroll container as hidden, which
    // would confuse "clipped by the card" with "below the fold".
    cy.viewport(1280, 1200)
    cy.loginAs('secondMember')
    visitProfile(memberProfile)

    card('about').contains('button', 'Read more').should('be.visible')
    assertAboutIsClipped(true)

    aboutCardHeight().then((collapsedHeight) => {
      cardPositions().then((collapsedPositions) => {
        card('about').contains('button', 'Read more').click()
        card('about').contains('button', 'Show less').should('exist')
        assertAboutIsClipped(false)
        aboutCardHeight().should('be.greaterThan', collapsedHeight)

        cardPositions().then((expandedPositions) => {
          for (const cardId of ['cover', 'avatar', 'full-name', 'bio']) {
            expect(expandedPositions[cardId], `${cardId} stayed put`).to.equal(
              collapsedPositions[cardId],
            )
          }
        })

        card('about').contains('button', 'Show less').click()
        card('about').contains('button', 'Read more').should('exist')
        assertAboutIsClipped(true)
        cardPositions().should('deep.equal', collapsedPositions)
      })
    })
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

function visitProfile(profile: string) {
  cy.visit(`/g/people/${profile}`)
  // The grid only mounts once the bento call resolves; the skeleton has no cards.
  return cy.get('article[data-profile-card-id]').should('exist')
}

function card(cardId: string) {
  return cy.get(`article[data-profile-card-id="${cardId}"]`)
}

function cardIdsInOrder() {
  return cy
    .get('article[data-profile-card-id]')
    .then(($cards) => $cards.toArray().map((element) => element.dataset.profileCardId))
}

/**
 * Each card's packed position, read from the inline transform the layout sets.
 * Independent of page scroll, unlike a bounding rect.
 */
function cardPositions() {
  return cy.get('[data-profile-card-wrapper]').then(($wrappers) => {
    const positions: Record<string, string> = {}
    $wrappers.toArray().forEach((element) => {
      positions[element.dataset.profileCardId as string] = element.style.transform
    })
    return positions
  })
}

function aboutCardHeight() {
  return card('about').then(($card) => $card[0].getBoundingClientRect().height)
}

/**
 * Whether the About card clips its own text, measured geometrically rather than
 * with `be.visible`: the card can sit outside the app's scroll container, which
 * Cypress also reports as hidden, so a visibility assertion would not be about
 * the collapse at all.
 */
function assertAboutIsClipped(clipped: boolean) {
  card('about').should(($card) => {
    const cardBottom = $card[0].getBoundingClientRect().bottom
    const paragraphs = $card.find('.prose p')
    const lastBottom = paragraphs[paragraphs.length - 1].getBoundingClientRect().bottom
    if (clipped) {
      expect(lastBottom, 'last About paragraph is cut off by the card').to.be.greaterThan(
        cardBottom,
      )
    } else {
      expect(lastBottom, 'last About paragraph fits inside the card').to.be.at.most(cardBottom)
    }
  })
}

function assertOnlyNameCard() {
  cy.get('article[data-profile-card-id]').should('have.length', 1)
  card('full-name').should('contain.text', personas.outsider.displayName)
  cy.contains(
    /no introduction|no profile page|build your profile|add image|click to upload/i,
  ).should('not.exist')
}

function labelledTextarea(label: string) {
  return cy
    .contains('label', label)
    .then(($label) => cy.get(`textarea[id="${$label.attr('for')}"]`))
}
