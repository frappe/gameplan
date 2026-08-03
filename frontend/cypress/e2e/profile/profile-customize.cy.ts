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
    // The editor aside, which holds the checklist, only exists from `md` up.
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
    // Bio is the empty field under test. `readme` keeps a value so the profile
    // page still renders a grid — on a wholly empty profile it shows the empty
    // state instead, and "no bio card" would then pass for the wrong reason.
    setProfileFields(memberProfile, {
      bio: '',
      readme: '<p>Still worth reading.</p>',
      image: '',
      cover_image: '',
    })

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

  it('restores the default layout, but only once the question is answered', () => {
    cy.loginAs('member')
    visitCustomize()

    // Nothing to restore until a layout is saved: the page already is the default.
    restoreButton().should('not.exist')
    checklistRow('cover_image').uncheck()
    saveLayout()
    cardIdsInOrder().should('deep.equal', ['avatar', 'full-name', 'bio', 'about'])

    // Cancelling is not "restore later", it is "do nothing".
    restoreButton().click()
    cy.get('[role="dialog"]').contains('button', 'Keep my layout').click()
    cardIdsInOrder().should('deep.equal', ['avatar', 'full-name', 'bio', 'about'])
    layoutCustomized(memberProfile).should('equal', 1)

    restoreDefaultLayout()

    cardIdsInOrder().should('deep.equal', defaultCardOrder)
    layoutCustomized(memberProfile).should('equal', 0)
    // Back behind the one-way door, so the notice returns and Save has nothing to do.
    cy.get('[data-profile-default-layout-notice]').should('be.visible')
    restoreButton().should('not.exist')
    headerSaveButton().should('be.disabled')
  })
})

// Two save speeds share this screen. A bound card's value belongs to the profile
// and is written the moment the control is committed; the layout stays a draft
// until Save. So a value edit must persist on its own, must never land on the
// bound row, and must not make the layout dirty.
describe('Profile customize editor — bound values', () => {
  let memberProfile: string

  beforeEach(() => {
    // The editor aside, which holds the value controls, only exists from `md` up.
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

  it('uploads a profile picture from the panel and shows it on the canvas', () => {
    cy.loginAs('member')
    visitCustomize()

    card('avatar').click()
    cy.intercept('POST', '**/method/set_image').as('setImage')
    panelFileInput().selectFile(pngFile('new-avatar.png'), { force: true })

    cy.wait('@setImage').its('response.statusCode').should('equal', 200)
    card('avatar').find('img').should('have.attr', 'src').and('include', '/files/')
  })

  it('saves a bio typed in the panel without making the layout dirty', () => {
    cy.loginAs('member')
    visitCustomize()

    card('bio').click()
    cy.intercept('PUT', '**/api/v2/document/GP%20User%20Profile/*').as('saveProfile')
    panelField('bio').clear().type('Now writing docs before code.').blur()

    cy.wait('@saveProfile').its('request.body.bio').should('equal', 'Now writing docs before code.')
    card('bio').should('contain.text', 'Now writing docs before code.')
    // The layout never changed, so Save has nothing to commit.
    headerSaveButton().should('be.disabled')
  })

  it('keeps a panel edit across a reload, with the layout still the default', () => {
    cy.loginAs('member')
    visitCustomize()

    card('bio').click()
    cy.intercept('PUT', '**/api/v2/document/GP%20User%20Profile/*').as('saveProfile')
    panelField('bio').clear().type('Written before it is built.').blur()
    cy.wait('@saveProfile')

    // Deliberately no Save: the value is already on the profile, the layout is not.
    cy.reload()
    cy.get('[data-profile-info-checklist]').should('be.visible')
    card('bio').should('contain.text', 'Written before it is built.')
    cardIdsInOrder().should('deep.equal', defaultCardOrder)
    layoutCustomized(memberProfile).should('equal', 0)
  })

  it('leaves the saved bound row empty after a bio edit', () => {
    cy.loginAs('member')
    visitCustomize()

    // Save first, so the layout is stored rows rather than the computed default.
    checklistRow('cover_image').uncheck()
    saveLayout()

    card('bio').click()
    cy.intercept('PUT', '**/api/v2/document/GP%20User%20Profile/*').as('saveProfile')
    panelField('bio').clear().type('Stored on the profile, not the card.').blur()
    cy.wait('@saveProfile')

    profileField(memberProfile, 'bio').should('equal', 'Stored on the profile, not the card.')
    bentoRow(memberProfile, 'bio').then((row) => {
      expect(row.source).to.equal('field')
      expect(row.field).to.equal('bio')
      expect(row.text || '').to.equal('')
      expect(row.image || '').to.equal('')
    })
  })

  it('fills a ticked but empty field from the panel', () => {
    // A profile with a name and nothing else, so the other four fields are empty.
    setProfileFields(memberProfile, { bio: '', readme: '', image: '', cover_image: '' })

    cy.loginAs('member')
    visitCustomize()

    checklistRow('bio').check()
    card('bio').find('[data-profile-card-empty]').should('contain.text', 'Bio — empty')

    cy.intercept('PUT', '**/api/v2/document/GP%20User%20Profile/*').as('saveProfile')
    panelField('bio').type('Filled in from the panel.').blur()
    cy.wait('@saveProfile')

    card('bio').find('[data-profile-card-empty]').should('not.exist')
    card('bio').should('contain.text', 'Filled in from the panel.')
  })

  it('edits About through the panel dialog', () => {
    cy.loginAs('member')
    visitCustomize()

    card('about').click()
    cy.intercept('PUT', '**/api/v2/document/GP%20User%20Profile/*').as('saveProfile')
    panel().contains('button', 'Edit about').click()
    cy.get('[role="dialog"]').find('[contenteditable=true]').should('be.visible')
    cy.get('[role="dialog"]').find('[contenteditable=true]').click().type(' And the rest.')
    cy.get('[role="dialog"]').contains('button', 'Save').click()

    cy.wait('@saveProfile').its('request.body.readme').should('contain', 'And the rest.')
    cy.get('[role="dialog"]').should('not.exist')
    card('about').should('contain.text', 'And the rest.')
    headerSaveButton().should('be.disabled')
  })

  it('repositions the bound cover onto the profile, not onto the draft row', () => {
    cy.loginAs('member')
    visitCustomize()

    card('cover').click()
    cy.intercept('POST', '**/method/set_cover_image_position').as('setCoverPosition')
    panel().contains('button', 'Reposition').click()
    card('cover').button('Save').click()

    cy.wait('@setCoverPosition').its('response.statusCode').should('equal', 200)
    // Saved without dragging, so the seeded position round-trips unchanged.
    profileField(memberProfile, 'cover_image_position').should('equal', 30)
    layoutCustomized(memberProfile).should('equal', 0)
    headerSaveButton().should('be.disabled')
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

function restoreButton() {
  return cy.get('button[data-profile-restore-default-layout]')
}

function restoreDefaultLayout() {
  cy.intercept('POST', '**/method/*reset_my_bento_cards').as('resetLayout')
  restoreButton().click()
  cy.get('[role="dialog"]').contains('button', 'Restore default').click()
  return cy.wait('@resetLayout').its('response.statusCode').should('equal', 200)
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

interface BentoRow {
  card_id: string
  source?: string
  field?: string
  text?: string
  image?: string
}

/** The saved child row for a card, read straight from the document. */
function bentoRow(profile: string, cardId: string) {
  return cy
    .request({ url: `/api/v2/document/GP User Profile/${encodeURIComponent(profile)}` })
    .then(({ body }) => {
      let rows = (body.data.bento_cards || []) as BentoRow[]
      let row = rows.find((bentoCard) => bentoCard.card_id === cardId)
      expect(row, `saved row for "${cardId}"`).to.exist
      return row as BentoRow
    })
}

/** The selected-card block of the editor aside. */
function panel() {
  return cy.get('aside')
}

function panelField(field: string) {
  return cy.get(`[data-profile-panel-field="${field}"]`)
}

/** The aside's only file input: a bound image card offers no other uploader. */
function panelFileInput() {
  return panel().find('input[type=file]')
}

/** The layout's Save button, told apart from a card's own Save controls. */
function headerSaveButton() {
  return cy.get('button[data-profile-save-layout]')
}

// A 1x1 PNG, so an upload is a real image without shipping a fixture file.
const onePixelPng =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='

function pngFile(fileName: string) {
  return {
    contents: Cypress.Buffer.from(onePixelPng, 'base64'),
    fileName,
    mimeType: 'image/png',
  }
}
