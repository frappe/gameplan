import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import path from 'path'
import { visualizer } from 'rollup-plugin-visualizer'
import { getProxyOptions } from 'frappe-ui/src/utils/vite-dev-server'
import { webserver_port } from '../../../sites/common_site_config.json'

export default defineConfig({
  plugins: [vue(), vueJsx(), visualizer({ emitFile: true })],
  server: {
    port: 8080,
    proxy: getProxyOptions({ port: webserver_port }),
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  optimizeDeps: {
    include: ['feather-icons', 'showdown'],
  },
  build: {
    outDir: '../gameplan/public/frontend',
    emptyOutDir: true,
    target: 'es2015',
  },
})
