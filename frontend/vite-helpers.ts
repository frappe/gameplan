import path from 'path'
import { existsSync } from 'node:fs'
import type { PluginOption } from 'vite'

interface LocalFrappeUIDevConfigParams {
  mode: string
  rootDir: string
}

interface LocalFrappeUIDevConfig {
  useLocalFrappeUI: boolean
  localFrappeUIPath: string
  localFrappeUIAliases: Record<string, string>
}

interface ImportFrappeUIPluginParams {
  useLocalFrappeUI: boolean
}

type FrappeUIPluginFactory = (...args: any[]) => PluginOption
type FrappeUIPluginModule = { default: FrappeUIPluginFactory }

async function loadFrappeUIPluginModule(modulePath: string): Promise<FrappeUIPluginModule> {
  return (await import(modulePath)) as FrappeUIPluginModule
}

export function getLocalFrappeUIDevConfig({
  mode,
  rootDir,
}: LocalFrappeUIDevConfigParams): LocalFrappeUIDevConfig {
  const isDev = mode === 'development'
  const localFrappeUIPath = path.resolve(rootDir, '../frappe-ui')
  const useLocalFrappeUI = isDev && existsSync(path.join(localFrappeUIPath, 'node_modules'))

  if (isDev && existsSync(localFrappeUIPath) && !useLocalFrappeUI) {
    console.warn('⚠️  Local frappe-ui found but dependencies not installed.')
    console.warn('   Run: cd ../frappe-ui && yarn install')
  }

  const localFrappeUIAliases: Record<string, string> = useLocalFrappeUI
    ? {
        // Subpath exports (./editor) must be aliased explicitly: the bare
        // `frappe-ui` alias rewrites to a directory path and bypasses the
        // package exports map, so `frappe-ui/editor` would not resolve in dev.
        'frappe-ui/editor': path.resolve(
          localFrappeUIPath,
          'src',
          'molecules',
          'editor',
          'index.ts',
        ),
        'frappe-ui/style.css': path.resolve(localFrappeUIPath, 'src', 'style.css'),
        'frappe-ui': localFrappeUIPath,
        // frappe-ui's editor source uses its own internal path aliases; when
        // consuming it as source in dev they must be mapped to frappe-ui's src.
        '@components': path.resolve(localFrappeUIPath, 'src', 'components'),
        '@molecules': path.resolve(localFrappeUIPath, 'src', 'molecules'),
        '@composables': path.resolve(localFrappeUIPath, 'src', 'composables'),
        '@utils': path.resolve(localFrappeUIPath, 'src', 'utils'),
      }
    : {}

  return {
    useLocalFrappeUI,
    localFrappeUIPath,
    localFrappeUIAliases,
  }
}

export async function importFrappeUIPlugin({
  useLocalFrappeUI,
}: ImportFrappeUIPluginParams): Promise<FrappeUIPluginFactory> {
  const npmModulePath = 'frappe-ui/vite'
  const modulePath = useLocalFrappeUI ? '../frappe-ui/vite/index.js' : npmModulePath

  try {
    const module = await loadFrappeUIPluginModule(modulePath)
    return module.default as FrappeUIPluginFactory
  } catch (error) {
    if (useLocalFrappeUI) {
      console.warn('⚠️  Failed to import local frappe-ui plugin, falling back to npm package')
      console.warn('   Error:', error instanceof Error ? error.message : String(error))
      const fallbackModule = await loadFrappeUIPluginModule(npmModulePath)
      return fallbackModule.default as FrappeUIPluginFactory
    }
    throw error
  }
}
