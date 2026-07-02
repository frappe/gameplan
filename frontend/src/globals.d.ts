// defining global components and properties here for autocompletion
// https://github.com/johnsoncodehk/volar/tree/master/extensions/vscode-vue-language-features

declare module '@vue/runtime-core' {
  export interface GlobalComponents {
    RouterLink: (typeof import('vue-router'))['RouterLink']
    RouterView: (typeof import('vue-router'))['RouterView']
    Button: (typeof import('frappe-ui'))['Button']
    Input: (typeof import('frappe-ui'))['Input']
    TextInput: (typeof import('frappe-ui'))['TextInput']
    ErrorMessage: (typeof import('frappe-ui'))['ErrorMessage']
    Dialog: (typeof import('frappe-ui'))['Dialog']
    FeatherIcon: (typeof import('frappe-ui'))['FeatherIcon']
    Alert: (typeof import('frappe-ui'))['Alert']
    Badge: (typeof import('frappe-ui'))['Badge']
    UserAvatar: typeof import('./components/UserAvatar.vue')
  }
}

declare global {
  interface ImportMetaEnv {
    readonly DEV: boolean
    readonly PROD: boolean
    readonly MODE: string
    readonly BASE_URL: string
    readonly SSR: boolean
  }

  interface ImportMeta {
    readonly env: ImportMetaEnv
  }

  interface Window {
    site_name: string
    gameplan_public_web_enabled?: boolean
    gameplan_frontend_sentry_dsn?: string | null
    is_public_visitor?: boolean
    max_file_size?: number | string | null
    read_only_mode?: boolean
    system_timezone?: string | null
  }
}

export {}
