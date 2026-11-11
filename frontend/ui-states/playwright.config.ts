import { defineConfig, devices } from '@playwright/test'
import { resolve } from 'node:path'

/**
 * Captures every Gameplan UI state as a screenshot, walking the machines
 * under `flows/`. Not a test suite: one run per flow, no retries, one worker.
 *
 * `BASE_URL` names a dev site (`pilot dev start`, which sets DEV_SERVER) with
 * `allow_tests` and `enable_ui_tests` set to 1. Every capture path calls
 * `gameplan.ui_test_helpers.reset`, which deletes all Gameplan data on that
 * site, so never point it at a site with data you want to keep.
 */
const baseURL = process.env.BASE_URL
if (!baseURL) throw new Error('BASE_URL must name the dev site to capture, such as http://gp-ui-states.localhost:8000')

export const OUT_DIR = resolve(import.meta.dirname, 'out')

export default defineConfig({
  testDir: import.meta.dirname,
  testMatch: /capture\.spec\.ts/,
  outputDir: resolve(import.meta.dirname, '.runs'),
  // Each path resets the whole site, so paths must never overlap.
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 20 * 60_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],
  use: {
    baseURL,
    viewport: { width: 1440, height: 900 },
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } }],
})
