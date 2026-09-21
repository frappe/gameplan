import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    communityScope?: boolean
    fullWidth?: boolean
    hideHeader?: boolean
    hideMobileNav?: boolean
  }
}
