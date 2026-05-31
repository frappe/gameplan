import frappeUIPreset from 'frappe-ui/tailwind'
import containerQueries from '@tailwindcss/container-queries'

export default {
  presets: [frappeUIPreset],
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
    './node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}',
    '../node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}',
    '../frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}',
    // The editor (and its string-based lucide-* icon classes) lives under
    // molecules; scan it so the icon mask utilities are emitted.
    './node_modules/frappe-ui/src/molecules/**/*.{vue,js,ts,jsx,tsx}',
    '../node_modules/frappe-ui/src/molecules/**/*.{vue,js,ts,jsx,tsx}',
    '../frappe-ui/src/molecules/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: {
        DEFAULT: '1rem',
        sm: '2rem',
        lg: '2rem',
        xl: '4rem',
        '2xl': '4rem',
      },
    },
    extend: {
      maxWidth: {
        'main-content': '768px',
      },
      screens: {
        standalone: {
          raw: '(display-mode: standalone)',
        },
      },
    },
  },
  plugins: [containerQueries],
}
