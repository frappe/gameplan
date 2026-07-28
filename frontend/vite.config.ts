import { defineConfig, type PluginOption } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import path from 'path'
import fs from 'fs'
import { visualizer } from 'rollup-plugin-visualizer'
import istanbul from 'vite-plugin-istanbul'
// @ts-expect-error frappe-ui/vite ships untyped JS; drop this once it gains types.
import frappeui from 'frappe-ui/vite'

// Instrumented only when GAMEPLAN_COVERAGE=1, which `ui-test.yml` sets for its build
// alone. Instrumentation roughly doubles bundle size and slows every expression, so
// it must never reach a production build — hence an explicit opt-in rather than a
// mode check, which `bench build` would trip.
const coverage = process.env.GAMEPLAN_COVERAGE === '1'

// Every file the instrumenter touched, with all counters still at zero.
//
// 33 of the app's routes are lazy `() => import(...)`, so a page no spec ever visits
// never registers in the browser's `window.__coverage__` and would drop out of the
// report entirely — inflating the percentage by shrinking the denominator instead of
// counting the file as 0%. Writing this baseline and merging it under the runtime
// data puts those files back at zero, which is the honest number.
const instrumented = new Map<string, unknown>()

// frappe-ui is resolved through node_modules — the published package by default,
// or the local ../frappe-ui checkout when symlinked via `yarn dev:local`. Either
// way its `exports`/`imports` maps drive resolution, so no aliases are needed here.
export default defineConfig({
  define: {
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
  },
  plugins: [
    frappeui({
      frontendRoute: '/g',
      frappeTypes: {
        input: {
          gameplan: [
            'gp_project',
            'gp_member',
            'gp_team',
            'gp_comment',
            'gp_discussion',
            'gp_page',
            'gp_task',
            'gp_poll',
            'gp_guest_access',
            'gp_invitation',
            'gp_user_profile',
            'gp_notification',
            'gp_activity',
            'gp_search_feedback',
            'gp_draft',
            'gp_tag',
            'gp_pinned_project',
            'gp_custom_emoji',
          ],
        },
      },
    }),
    vue(),
    vueJsx(),
    visualizer({ emitFile: true }) as PluginOption,
    // `extension` must list .vue explicitly: the plugin's default covers .js/.ts
    // only, which would silently report on the ~600 lines of utils and composables
    // and skip all 22k lines of components and pages. forceBuildInstrument and
    // checkProd are both required because Cypress runs against `bench build`
    // output, which is a production `vite build`.
    coverage &&
      (istanbul({
        include: 'src/*',
        extension: ['.js', '.ts', '.vue', '.jsx', '.tsx'],
        forceBuildInstrument: true,
        checkProd: false,
        onCover: (_fileName, fileCoverage) => {
          instrumented.set((fileCoverage as { path: string }).path, fileCoverage)
        },
      }) as PluginOption),
    coverage &&
      ({
        name: 'gameplan-coverage-baseline',
        closeBundle() {
          // Anchored to this config's directory, not the process CWD: `bench build`
          // does not necessarily invoke vite from frontend/.
          const dir = path.resolve(__dirname, 'coverage')
          fs.mkdirSync(dir, { recursive: true })
          fs.writeFileSync(
            path.join(dir, 'baseline.json'),
            JSON.stringify(Object.fromEntries(instrumented)),
          )
          console.log(`[coverage] baseline written for ${instrumented.size} files`)
        },
      } as PluginOption),
  ].filter(Boolean),
  server: {
    host: '0.0.0.0',
    allowedHosts: true,
    // Allow serving the symlinked checkout's real path (yarn dev:local).
    fs: {
      allow: ['..', 'node_modules', '../frappe-ui'],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
    // The symlinked frappe-ui checkout (yarn dev:frappe-ui) resolves @tiptap/pm
    // from its own node_modules, so every prosemirror package exists twice. Two
    // failure modes follow, and both need a single instance to avoid:
    //   1. instanceof breaks across copies (e.g. a DecorationSet built by a
    //      gameplan extension fails the editor view's instanceof check).
    //   2. Selection.jsonID() registers into prosemirror-state's module-level
    //      registry; once state is deduped to one registry, a second copy of
    //      gapcursor/tables re-registers the same id ("gapcursor"/"cell") and
    //      throws `RangeError: Duplicate use of selection JSON ID`, which aborts
    //      router navigation to any editor route (composer, discussion, page).
    // Dedupe the whole prosemirror family so exactly one copy of each loads.
    // vue/reka-ui/@vueuse/core exist twice for the same reason (the checkout's
    // own node_modules); two vue copies split the provide/inject and reactivity
    // worlds in production builds — reka-ui components throw missing-injection
    // errors and useFetch's hooks receive foreign-copy contexts. Dev masks all
    // of this because the dev server resolves through the import graph lazily.
    dedupe: [
      'vue',
      'vue-router',
      '@vueuse/core',
      'reka-ui',
      'prosemirror-changeset',
      'prosemirror-commands',
      'prosemirror-dropcursor',
      'prosemirror-gapcursor',
      'prosemirror-history',
      'prosemirror-inputrules',
      'prosemirror-keymap',
      'prosemirror-model',
      'prosemirror-schema-list',
      'prosemirror-state',
      'prosemirror-tables',
      'prosemirror-transform',
      'prosemirror-view',
    ],
  },
  optimizeDeps: {
    include: ['feather-icons'],
  },
})
