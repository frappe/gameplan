import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    communityScope?: boolean
    // Shows the community sidebar without scoping the route to a community (NotFound).
    communitySidebar?: boolean
    fullWidth?: boolean
    hideHeader?: boolean
    hideMobileNav?: boolean
    // Open to guests, rendered without the app shell and without loading app data.
    public?: boolean
  }
}
