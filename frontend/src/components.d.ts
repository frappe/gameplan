// defining global components here for autocompletion via volar
// https://github.com/johnsoncodehk/volar/tree/master/extensions/vscode-vue-language-features

declare module '@vue/runtime-core' {
  export interface GlobalComponents {
    RouterLink: typeof import('vue-router')['RouterLink']
    RouterView: typeof import('vue-router')['RouterView']
    Button: typeof import('frappe-ui')['Button']
    Input: typeof import('frappe-ui')['Input']
    TextInput: typeof import('frappe-ui')['TextInput']
    ErrorMessage: typeof import('frappe-ui')['ErrorMessage']
    Dialog: typeof import('frappe-ui')['Dialog']
    FeatherIcon: typeof import('frappe-ui')['FeatherIcon']
    Alert: typeof import('frappe-ui')['Alert']
    Badge: typeof import('frappe-ui')['Badge']
    UserInfo: typeof import('frappe-ui')['UserInfo']
    UserAvatar: typeof import('./components/UserAvatar.vue')
  }
}

export {}
