import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import path from 'path'
import { visualizer } from 'rollup-plugin-visualizer'
import frappeui from 'frappe-ui/vite'
import Icons from 'unplugin-icons/vite'
import Components from 'unplugin-vue-components/vite'
import IconsResolver from 'unplugin-icons/resolver'
import LucideIcons from './lucideIcons'

export default defineConfig({
  plugins: [
    frappeui(),
    vue(),
    vueJsx(),
    Components({
      resolvers: [
        IconsResolver({ prefix: false, enabledCollections: ['lucide'] }),
      ],
    }),
    Icons({
      customCollections: {
        lucide: LucideIcons,
      },
    }),
    visualizer({ emitFile: true }),
    {
      name: 'transform-index.html',
      transformIndexHtml(html, context) {
        if (!context.server) {
          return html.replace(
            /<\/body>/,
            `
            <script>
                {% for key in boot %}
                window["{{ key }}"] = {{ boot[key] | tojson }};
                {% endfor %}
            </script>
            </body>
            `
          )
        }
        return html
      },
    },
  ],
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
    commonjsOptions: {
      include: [/tailwind.config.js/, /node_modules/],
    },
    sourcemap: true,
  },
})
