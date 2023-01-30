import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import path from 'path'
import { visualizer } from 'rollup-plugin-visualizer'
import { getProxyOptions } from 'frappe-ui/src/utils/vite-dev-server'
import { webserver_port } from '../../../sites/common_site_config.json'
import Icons from 'unplugin-icons/vite'
import LucideIcons from './lucideIcons'

export default defineConfig({
  plugins: [
    vue(),
    vueJsx(),
    Icons({
      customCollections: {
        lucide: LucideIcons,
      },
    }),
    visualizer({ emitFile: true }),
  ],
  server: {
    port: 8080,
    proxy: getProxyOptions({ port: webserver_port }),
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
  build: {
    outDir: '../gameplan/public/frontend',
    emptyOutDir: true,
    target: 'es2015',
    commonjsOptions: {
      include: [/tailwind.config.js/, /node_modules/],
    },
  },
})
