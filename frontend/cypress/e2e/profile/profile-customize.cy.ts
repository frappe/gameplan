import { personas } from '../../support/personas'
import { resetData } from '../../support/seed'

// The customize editor is driven by one fact: which bound fields are in the
// layout. The "Profile info" checklist derives its ticks from that, so ticking a
// row adds the card and removing the card in the grid unticks the row. Saving is
// a one-way door out of the computed default, and what the editor shows is what
// the profile page renders afterwards.

const coverImage = '/assets/frappe/images/background.png'
const avatarImage = '/assets/frappe/images/default-avatar.png'

const defaultCardOrder = ['cover', 'avatar', 'full-name', 'bio', 'about']

describe('Profile customize editor', () => {
  let memberProfile: string

  beforeEach(() => {
    // The editor aside, which holds the checklist, only exists from `lg` up.
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
      })
    })
  })

  it('ticks every bound field that is already in the layout', () => {
    cy.loginAs('member')
    visitCustomize()

    cardIdsInOrder().should('deep.equal', defaultCardOrder)
    for (const field of ['cover_image', 'image', 'full_name', 'bio', 'readme']) {
      checklistRow(field).should('be.checked')
    }
    // Nothing saved yet, so the one-way-door notice is on screen.
    cy.get('[data-profile-default-layout-notice]').should('be.visible')
    cy.get('[data-profile-empty-layout-notice]').should('not.exist')
  })

  it('adds a card when a field is ticked and removes it when unticked', () => {
    cy.loginAs('member')
    visitCustomize()

    checklistRow('bio').uncheck()
    card('bio').should('not.exist')
    checklistRow('bio').should('not.be.checked')

    checklistRow('bio').check()
    card('bio').should('exist')
    // The value comes back with the card, not a placeholder: the field is filled.
    card('bio').should('contain.text', 'Async first, with written decisions.')
    card('bio').find('[data-profile-card-empty]').should('not.exist')
  })

  it('unticks the checklist row when the card is removed in the grid', () => {
    cy.loginAs('member')
    visitCustomize()

    card('about').find('button[aria-label="Remove profile card"]').click({ force: true })

    card('about').should('not.exist')
    checklistRow('readme').should('not.be.checked')
  })

  it('shows a placeholder for a ticked field with no value, and hides it on the profile', () => {
    // A profile with a name and nothing else, so the other four fields are empty.
    setProfileFields(memberProfile, { bio: '', readme: '', image: '', cover_image: '' })

    cy.loginAs('member')
    visitCustomize()

    checklistRow('bio').should('not.be.checked')
    checklistRow('bio').check()

    card('bio').find('[data-profile-card-empty]').should('contain.text', 'Bio — empty')
    saveLayout()

    // The profile page drops the empty bound card entirely — the placeholder is
    // an editor-only affordance.
    cy.visit(`/g/people/${memberProfile}`)
    cy.get('article[data-profile-card-id]').should('exist')
    card('bio').should('not.exist')
    cy.get('[data-profile-card-empty]').should('not.exist')
  })

  it('warns that an all-unticked layout leaves the profile page empty', () => {
    cy.loginAs('member')
    visitCustomize()

    for (const field of ['cover_image', 'image', 'full_name', 'bio', 'readme']) {
      checklistRow(field).uncheck()
    }

    cy.get('[data-profile-empty-layout-notice]').should('be.visible')
    cy.get('article[data-profile-card-id]').should('not.exist')
  })

  it('saves the layout the editor shows, and the profile page matches it', () => {
    cy.loginAs('member')
    visitCustomize()

    checklistRow('cover_image').uncheck()
    checklistRow('readme').uncheck()
    cardIdsInOrder().should('deep.equal', ['avatar', 'full-name', 'bio'])
    saveLayout()

    // Saved, so the layout is stored rows now and the notice is gone.
    cy.get('[data-profile-default-layout-notice]').should('not.exist')

    cy.visit(`/g/people/${memberProfile}`)
    cy.get('article[data-profile-card-id]').should('exist')
    cardIdsInOrder().should('deep.equal', ['avatar', 'full-name', 'bio'])
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

function visitCustomize() {
  cy.visit('/g/profile/customize')
  // The panel and the grid both mount once the bento call resolves.
  return cy.get('[data-profile-info-checklist]').should('be.visible')
}

function saveLayout() {
  cy.intercept('POST', '**/method/*save_my_bento_cards').as('saveLayout')
  cy.contains('button', 'Save').click()
  return cy.wait('@saveLayout').its('response.statusCode').should('equal', 200)
}

function checklistRow(field: string) {
  return cy.get(`input[data-profile-bound-field="${field}"]`)
}

function card(cardId: string) {
  return cy.get(`article[data-profile-card-id="${cardId}"]`)
}

function cardIdsInOrder() {
  return cy
    .get('article[data-profile-card-id]')
    .then(($cards) => $cards.toArray().map((element) => element.dataset.profileCardId))
}
