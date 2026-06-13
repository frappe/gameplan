import { defineConfig } from 'cypress'

export default defineConfig({
  // JUnit XML per spec; CI parses these to post a results comment on the PR
  // (replaces Cypress Cloud recording). [hash] keeps one file per spec.
  reporter: 'mocha-junit-reporter',
  reporterOptions: {
    mochaFile: 'cypress/results/results-[hash].xml',
    toConsole: true,
  },
  video: true,
  e2e: {
    baseUrl: 'http://gameplan-demo.test:8000',
    supportFile: 'cypress/support/e2e.ts',
    specPattern: 'cypress/e2e/**/*.{js,jsx,ts,tsx}',
  },
  retries: {
    runMode: 2,
    openMode: 0,
  },
})
