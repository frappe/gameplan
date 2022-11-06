const { defineConfig } = require('cypress')

module.exports = defineConfig({
  projectId: 'y2q697',
  e2e: {
    baseUrl: 'http://gameplan-demo.test:8000',
    adminPassword: 'admin',
  },
  retries: {
    runMode: 2,
    openMode: 0,
  }
})
