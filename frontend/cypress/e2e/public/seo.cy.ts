import { resetData, type SeedIds } from '../../support/seed'

describe('Public search indexing', () => {
  let ids: SeedIds

  beforeEach(() => {
    resetData('public_space').then((seeded) => {
      ids = seeded
    })
    cy.clearCookies()
  })

  function threadPath() {
    return `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}`
  }

  it('serves readable content, metadata and navigation before JavaScript runs', () => {
    cy.intercept('GET', '**/assets/**/*.js', {
      body: '',
      headers: { 'content-type': 'text/javascript' },
    })
    cy.visit(threadPath())
    cy.get('[data-public-content]').within(() => {
      cy.contains('h1', 'Welcome to Open Source').should('be.visible')
      cy.contains('Glad to be here.').should('be.visible')
      cy.contains('Ship it this week?').should('be.visible')
      cy.contains('a', 'Announcements').click()
    })
    cy.get('[data-public-content]').contains('a', 'Welcome to Open Source').should('be.visible')
    cy.get('link[rel="canonical"]')
      .should('have.attr', 'href')
      .and('include', `/space/${ids.space}/discussions`)
    cy.get('meta[property="og:title"]')
      .should('have.attr', 'content')
      .and('include', 'Announcements')
    cy.get('[data-public-content]').contains('a', 'Communities').click()
    cy.get('[data-public-content]').contains('a', 'Open Source').should('be.visible')
    cy.request(threadPath()).then(({ body, headers }) => {
      expect(headers['cache-control']).to.include('no-store')
      expect(body).to.include('name="description"')
      expect(body).not.to.match(/[\w.+-]+@example\.com/)
      expect(body).not.to.include('Members-only thread')
    })
  })

  it('keeps the community directory available after Vue starts', () => {
    cy.visit('/g')
    cy.contains('Open Source').should('be.visible')
    cy.location('pathname').should('match', /^\/g\/?$/)
  })

  it('publishes only public URLs and redirects stale slugs', () => {
    cy.request('/gameplan_sitemap.xml').then(({ body, headers }) => {
      expect(headers['content-type']).to.include('xml')
      expect(body).to.include('<sitemapindex')
      expect(body).to.include('section=discussions')
    })
    cy.request('/gameplan_sitemap.xml?section=discussions&page=1').then(({ body }) => {
      expect(body).to.include(threadPath())
      expect(body).not.to.include(`/discussion/${ids.hidden_discussion}/`)
      expect(body).to.include('<lastmod>')
    })
    cy.request('/robots.txt').its('body').should('include', '/gameplan_sitemap.xml')
    cy.request({
      url: threadPath().replace(ids.discussion_slug!, 'old-title'),
      followRedirect: false,
    }).then(({ status, headers }) => {
      expect(status).to.eq(301)
      expect(headers.location).to.eq(threadPath())
    })
  })

  it('links to later replies with an indexable page URL', () => {
    let lastReply: string
    cy.login()
    cy.then(() =>
      cy.request({
        method: 'POST',
        url: '/api/method/frappe.client.insert_many',
        body: {
          docs: Array.from({ length: 50 }, (_, i) => ({
            doctype: 'GP Comment',
            reference_doctype: 'GP Discussion',
            reference_name: ids.discussion,
            content: `<p>SEO pagination reply ${i + 1}</p>`,
          })),
        },
      }),
    ).then(({ body }) => {
      lastReply = String(body.message[49])
    })
    cy.clearCookies()
    cy.visit(threadPath())
    cy.intercept('GET', '**/gameplan.public_lists.comments*start=50*').as('laterReplies')
    cy.contains('a', 'Next page of replies').click()
    cy.location('search').should('eq', '?page=2')
    cy.get('.comments-timeline').should('be.visible')
    cy.wait('@laterReplies')
    cy.contains('SEO pagination reply 50').should('be.visible')
    cy.contains('Glad to be here.').should('not.exist')
    cy.get('link[rel="canonical"]').should('have.attr', 'href').and('include', '?page=2')
    cy.request(threadPath() + '?page=2')
      .its('body')
      .should('include', 'SEO pagination reply 50')
    cy.then(() =>
      cy.request({ url: threadPath() + `?comment=${lastReply}`, followRedirect: false }),
    ).then(({ status, headers }) => {
      expect(status).to.eq(301)
      expect(headers.location).to.eq(threadPath() + `?page=2&comment=${lastReply}`)
    })
  })
})
