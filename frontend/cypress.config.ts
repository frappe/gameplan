import { defineConfig } from 'cypress'

export default defineConfig({
  projectId: 'y2q697',
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
