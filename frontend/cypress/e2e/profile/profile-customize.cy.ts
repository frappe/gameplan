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

    expectCardOrder(defaultCardOrder)
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

    card('bio').find('[data-profile-card-empty]').should('contain.text', 'Add a short bio')
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
    expectCardOrder(['avatar', 'full-name', 'bio'])
    saveLayout()

    // Saved, so the layout is stored rows now and the notice is gone.
    cy.get('[data-profile-default-layout-notice]').should('not.exist')

    cy.visit(`/g/people/${memberProfile}`)
    cy.get('article[data-profile-card-id]').should('exist')
    expectCardOrder(['avatar', 'full-name', 'bio'])
  })

  it('reorders by where the dragged card is, not by where it was grabbed', () => {
    cy.loginAs('member')
    visitCustomize()

    // About is the widest card on the canvas, so a corner grab leaves the
    // pointer most of a card away from the middle. The middle is what decides
    // the drop, which is the only reading that matches what the drag looks like.
    let dropped = ['about', 'cover', 'avatar', 'full-name', 'bio']

    expectCardOrder(defaultCardOrder)
    dragCardOnto('about', 'cover', { grab: 'corner' })
    expectCardOrder(dropped)

    // The same gesture grabbed dead centre has to land in the same place.
    visitCustomize()
    expectCardOrder(defaultCardOrder)
    dragCardOnto('about', 'cover', { grab: 'centre' })
    expectCardOrder(dropped)
  })

  it('drops into the gutter between two cards, which is on neither of them', () => {
    cy.loginAs('member')
    visitCustomize()

    expectCardOrder(defaultCardOrder)

    // Full name sits mid-row with Bio beside it, so the seam on its right has a
    // card on either side and none under it. It means what it looks like: put
    // the card between those two. A reading that asks "which card am I over?"
    // has no answer here, and every seam is a dead strip down the canvas.
    dragCardOnto('about', 'full-name', { land: 'seam' })
    expectCardOrder(['cover', 'avatar', 'full-name', 'about', 'bio'])
  })

  it('moves a card past a row as soon as it clears the row', () => {
    cy.loginAs('member')
    visitCustomize()

    expectCardOrder(defaultCardOrder)

    // Avatar dragged down into the top-left of About, which is four columns
    // wide and two rows tall. Its middle is barely inside About and still 300px
    // from About's own middle, so anything that ranks cards by distance to their
    // centres leaves Avatar where it was until the drag is halfway down a
    // two-row card. Clearing the row it was in is enough: Avatar goes to the end
    // of that row, which is the last place before About.
    dragCardOnto('avatar', 'about', { land: 'top-left' })
    expectCardOrder(['cover', 'full-name', 'bio', 'avatar', 'about'])
  })

  it('scrolls the page while a card is held against the bottom edge', () => {
    // Short enough that the layout runs off the bottom of the screen. That is
    // the only case this exists for: without an autoscroll the gesture runs out
    // of screen long before it runs out of layout, and the cards below the fold
    // are unreachable in one drag.
    cy.viewport(1280, 600)
    cy.loginAs('member')
    visitCustomize()

    expectCardOrder(defaultCardOrder)
    settled('cover')

    cy.window().then((win) => {
      let scroller = shellScroller(win)
      let bounds = scroller.getBoundingClientRect()
      expect(
        scroller.scrollHeight,
        'the page is taller than the screen, so there is something to scroll to',
      ).to.be.greaterThan(scroller.clientHeight)
      expect(scroller.scrollTop, 'the page starts at the top').to.equal(0)

      let sourceElement = cardIn(win, 'cover')
      let source = sourceElement.getBoundingClientRect()
      let press = { x: source.left + source.width / 2, y: source.top + source.height / 2 }
      let begin = { x: press.x + 10, y: press.y + 10 }
      // Two pixels off the bottom of the scroll region: inside the hot zone, and
      // deep enough in it to run at close to full speed.
      let hold = { x: press.x, y: bounds.bottom - 2 }

      firePointer(win, sourceElement, 'pointerdown', press.x, press.y)
      firePointer(win, win, 'pointermove', begin.x, begin.y)
      cy.get('[data-profile-drag-ghost="true"]').should('exist')
      cy.then(() => firePointer(win, win, 'pointermove', hold.x, hold.y))

      // Nothing else is sent from here. A held pointer emits no events, so a
      // page that keeps moving proves the scroll has a loop of its own.
      cy.wrap(null).should(() => {
        expect(
          scroller.scrollTop,
          'the page keeps scrolling with the pointer standing still',
        ).to.be.closeTo(scroller.scrollHeight - scroller.clientHeight, 2)
      })

      cy.then(() => firePointer(win, win, 'pointerup', hold.x, hold.y))
      cy.get('[data-profile-drag-ghost="true"]').should('not.exist')
    })

    // The reorder has to follow the scroll, not just the pointer. The ghost holds
    // still on screen the whole time, so a drop that reads its travel in screen
    // space sees none of this and leaves the card exactly where it started.
    cy.get('article[data-profile-card-id]').should(($cards) => {
      let ids = cardIdsOf($cards)
      expect(ids, 'the card is still in the layout').to.include('cover')
      expect(ids[ids.length - 1], 'the card scrolled to the end and landed there').to.equal('cover')
    })
  })

  it('reorders from the keyboard, one place at a time', () => {
    cy.loginAs('member')
    visitCustomize()

    expectCardOrder(defaultCardOrder)

    // The step is through the list, not across the grid: what "one place later"
    // means is the same whatever shape the tiles happen to be.
    moveCard('avatar', 'ArrowRight')
    expectCardOrder(['cover', 'full-name', 'avatar', 'bio', 'about'])
    announcement().should('contain.text', 'Avatar moved to position 3 of 5')

    moveCard('avatar', 'ArrowLeft')
    expectCardOrder(defaultCardOrder)
    announcement().should('contain.text', 'Avatar moved to position 2 of 5')

    // Sending it to an end is one keystroke, so a card never has to be walked
    // the length of a long layout.
    moveCard('avatar', 'ArrowDown')
    expectCardOrder(['cover', 'full-name', 'bio', 'about', 'avatar'])

    moveCard('avatar', 'ArrowUp')
    expectCardOrder(['avatar', 'cover', 'full-name', 'bio', 'about'])
  })

  it('keeps the moved card focused and selected, and stops at the ends', () => {
    cy.loginAs('member')
    visitCustomize()

    expectCardOrder(defaultCardOrder)

    // The tiles re-render in the new order, which moves the focused element in
    // the DOM. Losing the focus there would make every move a one-off: the next
    // key press has nowhere to land.
    moveCard('cover', 'ArrowRight')
    cy.focused().should('have.attr', 'data-profile-card-id', 'cover')
    // A drop selects the card it moved, and so does this: the panel should be
    // editing whatever was just rearranged.
    card('cover').should('have.class', 'ring-2')

    moveCard('cover', 'ArrowLeft')
    expectCardOrder(defaultCardOrder)

    // Clamped, not wrapped. Nothing moves and nothing is announced, because
    // nothing happened.
    moveCard('cover', 'ArrowLeft')
    expectCardOrder(defaultCardOrder)
    announcement().should('contain.text', 'Cover image moved to position 1 of 5')
  })

  it('leaves a bare arrow key alone, so the page still scrolls', () => {
    cy.loginAs('member')
    visitCustomize()

    expectCardOrder(defaultCardOrder)

    // Without the modifier these belong to the scroller. A canvas taller than
    // the screen is the normal case, and it has to stay reachable.
    card('avatar').focus().trigger('keydown', { key: 'ArrowRight' })
    card('avatar').trigger('keydown', { key: 'ArrowDown' })
    expectCardOrder(defaultCardOrder)
    announcement().should(($region) => {
      expect($region.text().trim(), 'nothing moved, so nothing is announced').to.equal('')
    })
  })

  it('restores the default layout, but only once the question is answered', () => {
    cy.loginAs('member')
    visitCustomize()

    // Nothing to restore until a layout is saved: the page already is the default.
    restoreButton().should('not.exist')
    checklistRow('cover_image').uncheck()
    saveLayout()
    expectCardOrder(['avatar', 'full-name', 'bio', 'about'])

    // Cancelling is not "restore later", it is "do nothing".
    restoreButton().click()
    cy.get('[role="dialog"]').contains('button', 'Keep my layout').click()
    expectCardOrder(['avatar', 'full-name', 'bio', 'about'])
    layoutCustomized(memberProfile).should('equal', 1)

    restoreDefaultLayout()

    expectCardOrder(defaultCardOrder)
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
    expectCardOrder(defaultCardOrder)
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
    card('bio').find('[data-profile-card-empty]').should('contain.text', 'Add a short bio')

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

/**
 * Drag one card until its own middle lands on another card, holding it either
 * dead centre or by its bottom-right corner. Both must reorder the same way: the
 * grab offset moves the pointer, not the card.
 *
 * `land` says where the dragged card's middle ends up: the target's own middle,
 * the gutter just past its right edge, or barely inside its top-left corner.
 */
function dragCardOnto(
  sourceId: string,
  targetId: string,
  options: { grab?: 'centre' | 'corner'; land?: 'middle' | 'seam' | 'top-left' } = {},
) {
  let { grab = 'centre', land = 'middle' } = options

  settled(sourceId)
  settled(targetId)

  cy.window().then((win) => {
    let sourceElement = cardIn(win, sourceId)
    let source = sourceElement.getBoundingClientRect()
    let target = cardIn(win, targetId).getBoundingClientRect()

    let press =
      grab === 'centre'
        ? { x: source.left + source.width / 2, y: source.top + source.height / 2 }
        : { x: source.right - 20, y: source.bottom - 20 }
    // The drag starts on the first move past the 6px threshold, and the grab
    // offset is read from that move, so it is the point to measure from.
    let begin = { x: press.x + 10, y: press.y + 10 }
    let offset = { x: begin.x - source.left, y: begin.y - source.top }
    // `middle` stops just short of it, so a reading that splits the target in
    // two is decided rather than sitting on the boundary.
    let landing = {
      middle: { x: target.left + target.width / 2 - 4, y: target.top + target.height / 2 - 4 },
      seam: { x: target.right + 6, y: target.top + target.height / 2 },
      'top-left': { x: target.left + target.width / 4, y: target.top + target.height / 8 },
    }[land]
    // The pointer, worked back from where the dragged card has to end up.
    let drop = {
      x: landing.x - source.width / 2 + offset.x,
      y: landing.y - source.height / 2 + offset.y,
    }

    // A frame between each step, because picking the card up is asynchronous:
    // the grid only starts the floating drag on the move that passes its 6px
    // threshold, and awaits a tick before the next move can find it.
    firePointer(win, sourceElement, 'pointerdown', press.x, press.y)
    firePointer(win, win, 'pointermove', begin.x, begin.y)
    cy.get('[data-profile-drag-ghost="true"]').should('exist')
    cy.then(() => firePointer(win, win, 'pointermove', drop.x, drop.y))
    cy.then(() => firePointer(win, win, 'pointerup', drop.x, drop.y))
    // The ghost is a card too, so it would show up in the order being asserted.
    cy.get('[data-profile-drag-ghost="true"]').should('not.exist')
  })
}

/**
 * Move a focused card with the keyboard.
 *
 * Both modifiers at once, because the card accepts either and a spec should not
 * care which machine it is running on. The event is built in the app's own
 * realm for the same reason the pointer events are: the handler is `.self`, so
 * it only answers an event whose target is the card element itself.
 */
function moveCard(cardId: string, key: string) {
  return cy.window().then((win) => {
    let element = cardIn(win, cardId)
    element.focus()
    element.dispatchEvent(
      new win.KeyboardEvent('keydown', {
        key,
        metaKey: true,
        ctrlKey: true,
        bubbles: true,
        cancelable: true,
      }),
    )
  })
}

/** The live region the grid speaks a keyboard reorder through. */
function announcement() {
  return cy.get('[data-profile-reorder-announcement]')
}

function cardIn(win: Window, cardId: string) {
  return win.document.querySelector(`article[data-profile-card-id="${cardId}"]`) as HTMLElement
}

/**
 * The shell's scroll region, which is what the customize canvas rides.
 *
 * `data-slot` is frappe-ui's own hook for reaching into a shell. The step
 * through it is what keeps this off the editor panel's ScrollArea, which
 * carries the same reka viewport attribute and scrolls separately.
 */
function shellScroller(win: Window) {
  return win.document.querySelector(
    '[data-slot="desktop-shell-content"] > * > [data-reka-scroll-area-viewport]',
  ) as HTMLElement
}

/**
 * Wait until a card has stopped moving.
 *
 * Every tile carries a 200ms transition on width, height and transform, so a
 * rect read while the canvas is still settling is neither the size the card had
 * nor the size it is about to have. The inline style is the destination the
 * packer wrote, so the card has arrived when its rect agrees with it. Waiting
 * merely for "bigger than a placeholder" samples a different frame every run,
 * and the drop point lands somewhere different each time.
 */
function settled(cardId: string) {
  cy.get(`[data-profile-card-wrapper="true"][data-profile-card-id="${cardId}"]`).should(
    ($wrapper) => {
      let element = $wrapper[0]
      let declared = Number.parseFloat(element.style.width)
      expect(declared, 'the packer has given the card a width').to.be.greaterThan(0)
      expect(element.getBoundingClientRect().width).to.be.closeTo(declared, 0.5)
    },
  )
}

/** A pointer event built in the app's own realm, so its handlers accept it. */
function firePointer(win: Window, target: EventTarget, type: string, x: number, y: number) {
  target.dispatchEvent(
    new win.PointerEvent(type, {
      clientX: x,
      clientY: y,
      bubbles: true,
      cancelable: true,
      pointerId: 1,
      isPrimary: true,
      button: 0,
      buttons: 1,
    }),
  )
}

/**
 * Wait until the canvas renders exactly this order.
 *
 * The assertion goes inside `should` rather than after a `then` that maps the
 * ids out first. `cy.get(...).should(callback)` re-runs the query on every
 * retry; a `then` runs once and freezes whatever the DOM held at that instant,
 * so a reorder landing a tick later is never seen however long the assertion
 * waits for it.
 */
function expectCardOrder(expected: string[]) {
  return cy.get('article[data-profile-card-id]').should(($cards) => {
    expect(cardIdsOf($cards)).to.deep.equal(expected)
  })
}

function cardIdsOf($cards: JQuery<HTMLElement>) {
  return $cards.toArray().map((element) => element.dataset.profileCardId)
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
