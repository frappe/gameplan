import { onMounted, ref, type Ref } from 'vue'

export type Theme = 'light' | 'dark' | 'system'

const THEME_COLORS = {
  light: '#ffffff',
  dark: '#171717',
} as const

const currentTheme: Ref<Theme> = ref('light')
let isInitialized = false

const getSystemTheme = (): 'light' | 'dark' => {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

const applyTheme = (theme: Theme): void => {
  const resolvedTheme = theme === 'system' ? getSystemTheme() : theme
  document.documentElement.setAttribute('data-theme', resolvedTheme)
  updateThemeMeta(resolvedTheme)
}

const updateThemeMeta = (theme: 'light' | 'dark'): void => {
  document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]').forEach((meta) => {
    meta.content = THEME_COLORS[theme]
  })

  const statusBarStyle = document.querySelector<HTMLMetaElement>(
    'meta[name="apple-mobile-web-app-status-bar-style"]',
  )
  if (statusBarStyle) {
    statusBarStyle.content = theme === 'dark' ? 'black-translucent' : 'default'
  }
}

const handleSystemThemeChange = () => {
  if (currentTheme.value === 'system') {
    applyTheme('system')
  }
}

const initializeTheme = (): void => {
  if (isInitialized) return

  const storedTheme = localStorage.getItem('theme') as Theme | null
  currentTheme.value =
    storedTheme && ['light', 'dark', 'system'].includes(storedTheme) ? storedTheme : 'system'
  applyTheme(currentTheme.value)

  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaQuery.addEventListener('change', handleSystemThemeChange)
  isInitialized = true
}

const setTheme = (theme: Theme): void => {
  currentTheme.value = theme
  applyTheme(theme)
  localStorage.setItem('theme', theme)
}

const THEME_CYCLE: Theme[] = ['light', 'dark', 'system']

export function useTheme() {
  const toggleTheme = (): void => {
    const theme: Theme = currentTheme.value === 'dark' ? 'light' : 'dark'
    setTheme(theme)
  }

  const cycleTheme = (): void => {
    const next = (THEME_CYCLE.indexOf(currentTheme.value) + 1) % THEME_CYCLE.length
    setTheme(THEME_CYCLE[next])
  }

  onMounted(() => {
    initializeTheme()
  })

  return {
    currentTheme,
    toggleTheme,
    cycleTheme,
    setTheme,
    initializeTheme,
    getSystemTheme,
  }
}
