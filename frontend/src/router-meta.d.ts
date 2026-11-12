import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    communityScope?: boolean
    fullWidth?: boolean
    hideHeader?: boolean
    hideMobileNav?: boolean
    /**
     * Download the page's code while the browser is idle (see `prefetchPages`). Set it on
     * the pages people move between from the rail, the sidebar and the tab bar. `'last'`
     * fetches it after the others, for a page whose code is large.
     */
    prefetch?: boolean | 'last'
  }
}
