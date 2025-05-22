import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import path from 'path'
import { visualizer } from 'rollup-plugin-visualizer'
import frappeui from 'frappe-ui/vite'

export default defineConfig({
  define: {
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
  },
  plugins: [
    frappeui({
      frappeProxy: true,
      lucideIcons: true,
      jinjaBootData: true,
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
          ],
        },
      },
      buildConfig: {
        indexHtmlPath: '../gameplan/www/g.html',
      },
    }),
    vue(),
    vueJsx(),
    visualizer({ emitFile: true }),
  ],
  server: {
    allowedHosts: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      'tailwind.config.js': path.resolve(__dirname, 'tailwind.config.js'),
    },
  },
  optimizeDeps: {
    include: ['feather-icons', 'showdown', 'tailwind.config.js'],
  },
})
