import { resetData, type SeedIds } from '../../support/seed'

const names = [
  'Aarav Shah',
  'Maya Patel',
  'Noah Williams',
  'Zara Khan',
  'Leo Martin',
  'Sara Ahmed',
  'Owen Clark',
  'Priya Rao',
  'Liam Davis',
  'Nina Thomas',
  'Adam Lewis',
  'Emma Wilson',
  'Ravi Kumar',
  'Sofia Garcia',
  'Ryan Scott',
  'Aisha Ali',
  'Ethan Moore',
  'Anika Singh',
  'Daniel Lee',
  'Mira Johnson',
]

describe('Space access dialog with a long member list', () => {
  let ids: SeedIds

  beforeEach(() => {
    resetData('public_space').then((seeded) => {
      ids = seeded
      return cy.request('POST', '/api/method/frappe.client.insert_many', {
        docs: names.map((name, i) => ({
          doctype: 'User',
          email: `access-layout-${i}@example.com`,
          first_name: name,
          send_welcome_email: 0,
          roles: [{ role: 'Gameplan Member' }],
        })),
      })
    })
    cy.then(() =>
      cy.request('POST', '/api/method/frappe.client.set_value', {
        doctype: 'GP Team',
        name: ids.community,
        fieldname: {
          members: [
            { user: 'member@example.com', is_admin: 1 },
            { user: 'member2@example.com' },
            ...names.map((_, i) => ({ user: `access-layout-${i}@example.com` })),
          ],
        },
      }),
    )
    cy.then(() =>
      cy.request('POST', '/api/method/frappe.client.set_value', {
        doctype: 'GP Project',
        name: ids.private_space,
        fieldname: {
          members: [
            { user: 'member@example.com' },
            ...names.map((_, i) => ({ user: `access-layout-${i}@example.com` })),
          ],
        },
      }),
    )
  })

  for (const { entry, width, height } of [
    { entry: 'space', width: 1280, height: 800 },
    { entry: 'settings', width: 1280, height: 800 },
    { entry: 'settings', width: 390, height: 844 },
    { entry: 'space', width: 1280, height: 600 },
  ]) {
    it(`keeps access and nested visibility centered from ${entry} at ${width}x${height}`, () => {
      cy.viewport(width, height)
      if (entry === 'settings') {
        cy.visit(`/g/settings/communities/${ids.community}/spaces`)
        cy.iconButton('Core Team Space Options').click()
        cy.contains('[role="menuitem"]', 'Visibility').click()
      } else {
        cy.visit(`/g/community/${ids.community}/space/${ids.private_space}/discussions`)
        cy.get('button[aria-label="Space actions"]:visible').click()
        cy.contains('[role="menuitem"]', 'Visibility').click()
      }
      cy.contains('[role="dialog"]', 'Space access').as('access')
      cy.get('@access').contains('Aarav Shah').should('exist')
      const evidence = Cypress.env('ACCESS_DIALOG_EVIDENCE')
      const screenshotPrefix = `${evidence}-${entry}-${width}x${height}`
      if (evidence) cy.screenshot(`${screenshotPrefix}-member-list`, { capture: 'viewport' })
      cy.get('@access').find('button[aria-label="Change visibility"]').click()
      cy.contains('[role="dialog"]', 'Visibility of Core Team')
        .as('visibility')
        .should('be.visible')
      if (evidence) cy.screenshot(`${screenshotPrefix}-nested-visibility`, { capture: 'viewport' })
      cy.get('@visibility').should(($dialog) => {
        const rect = $dialog[0].getBoundingClientRect()
        const win = $dialog[0].ownerDocument.defaultView!
        expect(Math.abs(rect.left + rect.width / 2 - win.innerWidth / 2)).to.be.lessThan(2)
        expect(Math.abs(rect.top + rect.height / 2 - win.innerHeight / 2)).to.be.lessThan(2)
      })
      cy.get('@visibility').find('button[aria-label="Close"]').click()
      cy.get('@visibility').should('not.exist')
      cy.get('@access').should(($dialog) => {
        const outer = $dialog[0].closest('.dialog-scroll-container')!
        expect(outer.scrollHeight).to.be.at.most(outer.clientHeight + 1)
        const rect = $dialog[0].getBoundingClientRect()
        expect(Math.abs(rect.left + rect.width / 2 - width / 2)).to.be.lessThan(2)
        expect(rect.top).to.be.at.least(0)
        expect(rect.bottom).to.be.at.most(height)
      })
      cy.get('@access').find('[data-slot="scroll-area-viewport"]').scrollTo('bottom')
      cy.get('@access').contains('Mira Johnson').should('be.visible')
      cy.get('@access').find('button[aria-label="Close"]').should('be.visible')
    })
  }
})
