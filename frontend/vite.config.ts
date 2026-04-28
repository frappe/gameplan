import { defineConfig, type PluginOption, type UserConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import path from 'path'
import { visualizer } from 'rollup-plugin-visualizer'
import { getLocalFrappeUIDevConfig, importFrappeUIPlugin } from './vite-helpers'

export default defineConfig(async ({ mode }): Promise<UserConfig> => {
  const { useLocalFrappeUI, localFrappeUIAliases } = getLocalFrappeUIDevConfig({
    mode,
    rootDir: __dirname,
  })

  const frappeui = await importFrappeUIPlugin({ useLocalFrappeUI })

  const baseAliases = {
    '@': path.resolve(__dirname, 'src'),
  }

  return {
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
            ],
          },
        },
      }),
      vue(),
      vueJsx(),
      visualizer({ emitFile: true }) as PluginOption,
    ],
    server: {
      host: '0.0.0.0',
      allowedHosts: true,
      fs: {
        allow: ['..', 'node_modules', '../frappe-ui'],
      },
    },
    resolve: {
      alias: {
        ...localFrappeUIAliases,
        ...baseAliases,
      },
    },
    optimizeDeps: {
      include: ['feather-icons'],
    },
  }
})
