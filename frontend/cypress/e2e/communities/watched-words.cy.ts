import { resetData, type SeedIds } from '../../support/seed'

function settings(ids: SeedIds) {
  cy.visit(`/g/community/${ids.community}/moderation`)
  cy.contains('button', /^Watched words$/).click()
}
function rule(ids: SeedIds, action: string, word: string) {
  cy.request('POST', '/api/method/gameplan.watched_words.add', {
    community: ids.community,
    action,
    word,
  })
}
function thread(ids: SeedIds) {
  cy.visit(`/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}`)
  cy.contains('h1', 'Welcome thread').should('be.visible')
}
function editPost(text: string) {
  cy.selectDropdownOption('Discussion Options', 'Edit')
  cy.get('[contenteditable=true]').should('have.length', 1).click().type(`{selectall}${text}`)
  cy.contains('button', /^\s*Save\s*$/).click()
}

describe('Watched words', () => {
  it('previews and imports CSV, adds a manual rule, tests matching, and exports CSV', () => {
    resetData('space_with_discussion').then((ids) => {
      settings(ids)
      cy.get('input[type=file]').selectFile(
        {
          contents: Cypress.Buffer.from('spamword\n"buy, now",,true\nSPAMWORD\n'),
          fileName: 'words.csv',
          mimeType: 'text/csv',
        },
        { force: true },
      )
      cy.get('[role=dialog]')
        .should('contain.text', '2 new rules')
        .and('contain.text', '1 duplicates skipped')
      cy.request(
        '/api/method/gameplan.watched_words.rules?community=' + ids.community + '&action=Block',
      )
        .its('body.message.items')
        .should('have.length', 0)
      cy.get('[role=dialog]').contains('button', 'Import 2 rules').click()
      cy.contains('Watched words imported').should('be.visible')
      cy.get('input[placeholder="Word or phrase"]').type('forbiddenphrase')
      cy.contains('button', /^Add rule$/).click()
      cy.contains('span', 'forbiddenphrase').should('be.visible')
      cy.get('textarea[placeholder="Test words or a post"]').type('SPAMWORD')
      cy.contains('button', /^Test rules$/).click()
      cy.contains('p', 'Block: spamword').should('be.visible')
      cy.request(
        '/api/method/gameplan.watched_words.download?community=' + ids.community + '&action=Block',
      ).then(({ body }) => {
        expect(body).to.include('spamword').and.include('forbiddenphrase')
      })
    })
  })

  it('blocks a member submission and keeps its editable draft', () => {
    resetData('space_with_discussion').then((ids) => {
      rule(ids, 'Block', 'forbiddenphrase')
      cy.switchUser('secondMember')
      cy.visit(`/g/community/${ids.community}/new-discussion?spaceId=${ids.space}`)
      cy.get('textarea[placeholder="Title"]').type('Blocked content')
      cy.get('[contenteditable=true]').click().type('forbiddenphrase')
      cy.contains('button:visible', /^\s*Publish\s*$/).click()
      cy.contains('Remove the blocked words or phrases: forbiddenphrase').should('be.visible')
      cy.get('[contenteditable=true]').should('contain.text', 'forbiddenphrase')
      cy.location('pathname').should('include', 'new-discussion')
    })
  })

  it('censors ordinary API/page reads while the author edits the original', () => {
    resetData('space_with_discussion').then((ids) => {
      cy.request('PUT', `/api/v2/document/GP Discussion/${ids.discussion}`, {
        content: '<p>secretword</p>',
      })
      rule(ids, 'Censor', 'secretword')
      cy.switchUser('member')
      thread(ids)
      cy.contains('p', '■■■■■■■■■■').should('be.visible')
      cy.request(
        `/api/v2/document/GP Discussion?fields=["content"]&filters={"name":"${ids.discussion}"}`,
      ).then(({ body }) => {
        expect(body.data[0].content).to.include('■■■■■■■■■■').and.not.include('secretword')
        expect(body.data[0]).not.to.have.property('_watched_project')
      })
      cy.request(
        `/api/v2/document/GP Discussion?fields=["content as body"]&filters={"name":"${ids.discussion}"}`,
      )
        .its('body.data.0.body')
        .should('include', '■■■■■■■■■■')
      editPost('secretword refined')
      cy.contains('p', '■■■■■■■■■■ refined').should('be.visible')
      cy.request(
        `/api/method/gameplan.watched_word_edits.original?doctype=GP Discussion&name=${ids.discussion}`,
      )
        .its('body.message.content')
        .should('include', 'secretword refined')
    })
  })

  it('holds an edit privately and applies it to the same post after approval', () => {
    resetData('space_with_discussion').then((ids) => {
      rule(ids, 'Require approval', 'reviewme')
      cy.switchUser('member')
      thread(ids)
      editPost('reviewme proposed edit')
      cy.contains('Edit submitted for moderator approval').should('be.visible')
      cy.contains('p', 'Seed content').should('be.visible')
      cy.switchUser('admin')
      cy.visit(`/g/community/${ids.community}/moderation`)
      cy.contains('button', /^Approvals$/).click()
      cy.contains('Edit: Welcome thread').should('be.visible')
      cy.contains('button', /^Review$/).click()
      cy.get('[role=dialog]')
        .contains('button:not([role=combobox])', /^Approve$/)
        .click()
      cy.contains('No pending submissions.').should('be.visible')
      thread(ids)
      cy.contains('p', 'reviewme proposed edit').should('be.visible')
    })
  })

  it('shows automatic flags in the existing report queue', () => {
    resetData('space_with_discussion').then((ids) => {
      rule(ids, 'Flag', 'checkthis')
      cy.switchUser('secondMember')
      cy.request('POST', '/api/method/gameplan.approvals.submit', {
        doctype: 'GP Comment',
        request_key: 'auto-flag-ui',
        discussion: String(ids.discussion),
        content: '<p>checkthis</p>',
      })
      cy.switchUser('admin')
      cy.visit(`/g/community/${ids.community}/moderation`)
      cy.contains('button', /^Reports$/).click()
      cy.contains('button', /^Review$/).click()
      cy.get('[role=dialog]').contains('Automatic watched-word rule').should('be.visible')
    })
  })
})
