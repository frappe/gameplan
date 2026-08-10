import {
  createRouter,
  createWebHistory,
  type RouteLocationNormalized,
  type RouteLocationRaw,
  type RouteRecordRaw,
} from 'vue-router'
import { until } from '@vueuse/core'
import { watch } from 'vue'
import { call } from 'frappe-ui'
import { session } from './data/session'
import { users, usersReady } from './data/users'
import { communities, getCommunity } from './data/communities'
import { spaces, getSpace } from './data/spaces'
import type { Space } from './data/spaces'
import { communityState } from './data/communityState'
import { settingsBackgroundPath } from './components/Settings'
import { getScrollContainer, scrollTo } from 'frappe-ui'
import { isBrowserOffline, isNetworkError } from './offline'

declare const __FRONTEND_ROUTE__: string

type ResourceLike = {
  isFinished?: boolean
  data?: unknown
  error?: unknown
}

type RouteParamValue = string | string[]
type ContentRouteDescriptor = {
  doctype: 'GP Discussion' | 'GP Page' | 'GP Task'
  documentParam: 'postId' | 'pageId' | 'taskId'
  routeName: 'Discussion' | 'SpacePage' | 'SpaceTask'
  slugParam?: 'slug'
}
type ProjectContentDoc = {
  name: string
  project?: string
  slug?: string
}

const discussionFeeds = ['recent', 'unread', 'participating']
const projectContentDocRequests = new Map<string, Promise<ProjectContentDoc | null | undefined>>()
const OFFLINE_CACHE_HYDRATION_TIMEOUT = 3000

// Redirect-style guards still need a component record so Vue Router matches them consistently.
const RouteGuard = { render: () => null }

function routeParam(value: RouteParamValue): string {
  return Array.isArray(value) ? (value[0] ?? '') : value
}

function optionalRouteParam(value: RouteParamValue | undefined): string | undefined {
  if (!value) return undefined

  const resolvedValue = routeParam(value)
  return resolvedValue || undefined
}

function redirectOldSpacesRoute(to: RouteLocationNormalized): RouteLocationRaw {
  const queryTeamId = to.query.teamId
  const communityId = Array.isArray(queryTeamId) ? queryTeamId[0] : queryTeamId

  if (typeof communityId === 'string' && communityId) {
    return { name: 'Discussions', params: { communityId }, query: {} }
  }

  return getHomeRoute()
}

/**
 * `/:teamId` is the legacy single-segment community URL. It matches anything, so a stale
 * link such as `/g/teams` (the app lived at `/teams` before it moved to `/g`) used to be
 * read as a community id and land on the 404 page. Only redirect when the community really
 * exists; send everything else home.
 */
async function redirectLegacyTeamRoute(to: RouteLocationNormalized): Promise<RouteLocationRaw> {
  await ensureCommunityDataLoaded()

  const communityId = routeParam(to.params.teamId)
  if (!communityId || !getCommunity(communityId)) {
    return getHomeRoute()
  }

  return { name: 'Discussions', params: { communityId } }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    alias: '',
    component: RouteGuard,
    async beforeEnter() {
      await ensureCommunityDataLoaded()
      return getHomeRoute()
    },
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/pages/MobileHome.vue'),
    async beforeEnter() {
      await ensureCommunityDataLoaded()

      if (isMobileViewport() && communityState.id) {
        return
      }

      return getDesktopHomeRoute()
    },
  },
  {
    path: '/community',
    component: RouteGuard,
    async beforeEnter() {
      await ensureCommunityDataLoaded()
      return getHomeRoute()
    },
  },
  {
    path: '/community/:communityId',
    redirect: (to) => ({
      name: 'Discussions',
      params: { communityId: routeParam(to.params.communityId) },
    }),
  },
  {
    // Legacy path: the community menu is now a bottom sheet on the discussions header.
    path: '/community/:communityId/menu',
    redirect: (to) => ({
      name: 'Discussions',
      params: { communityId: routeParam(to.params.communityId) },
    }),
  },
  {
    name: 'Discussions',
    path: '/community/:communityId/discussions',
    component: () => import('@/pages/Discussions.vue'),
    props: true,
    meta: { communityScope: true },
  },
  {
    name: 'DiscussionsTab',
    path: '/community/:communityId/discussions/:feedType',
    component: () => import('@/pages/Discussions.vue'),
    props: true,
    meta: { communityScope: true },
    beforeEnter(to) {
      const feedType = routeParam(to.params.feedType)

      if (feedType === 'bookmarks') {
        return { name: 'Bookmarks' }
      }

      if (discussionFeeds.includes(feedType)) {
        return
      }

      return {
        name: 'DiscussionsTab',
        params: { communityId: routeParam(to.params.communityId), feedType: 'recent' },
        replace: true,
      }
    },
  },
  {
    path: '/discussions',
    component: RouteGuard,
    async beforeEnter() {
      await ensureCommunityDataLoaded()

      // `/discussions` stays as a compatibility entry point, but there is no global feed anymore.
      if (!communityState.id) {
        return getHomeRoute()
      }

      return {
        name: 'Discussions',
        params: { communityId: communityState.id },
      }
    },
  },
  {
    path: '/discussions/:feedType',
    component: RouteGuard,
    async beforeEnter(to) {
      await ensureCommunityDataLoaded()

      const feedType = routeParam(to.params.feedType)
      if (feedType === 'bookmarks') {
        return { name: 'Bookmarks' }
      }

      if (!communityState.id) {
        return getHomeRoute()
      }

      return {
        name: 'DiscussionsTab',
        params: {
          communityId: communityState.id,
          feedType: discussionFeeds.includes(feedType) ? feedType : 'recent',
        },
      }
    },
  },
  {
    name: 'Bookmarks',
    path: '/bookmarks',
    component: () => import('@/pages/Bookmarks.vue'),
  },
  {
    name: 'Drafts',
    path: '/drafts',
    component: () => import('@/pages/Drafts.vue'),
  },
  {
    name: 'MyTasks',
    path: '/tasks',
    component: () => import('@/pages/MyTasks.vue'),
  },
  {
    name: 'Task',
    path: '/task/:taskId',
    component: () => import('@/pages/Task.vue'),
    props: true,
  },
  {
    name: 'MyPages',
    path: '/pages',
    component: () => import('@/pages/MyPages.vue'),
  },
  {
    name: 'Page',
    path: '/page/:pageId/:slug?',
    component: () => import('@/pages/Page.vue'),
    props: true,
  },
  {
    path: '/people',
    name: 'People',
    component: () => import('@/pages/People.vue'),
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('@/pages/Search.vue'),
  },
  {
    path: '/onboarding',
    name: 'Onboarding',
    component: () => import('@/pages/Onboarding.vue'),
    async beforeEnter() {
      await ensureCommunityDataLoaded()

      if (hasAnyData()) {
        return getHomeRoute()
      }
    },
  },
  {
    path: '/no-communities',
    name: 'NoCommunities',
    component: () => import('@/pages/NoCommunities.vue'),
  },
  {
    path: '/404',
    name: 'NotFound',
    component: () => import('@/pages/NotFound.vue'),
  },
  {
    path: '/list',
    name: 'Teams',
    component: () => import('@/pages/Teams.vue'),
  },
  {
    path: '/spaces',
    redirect: redirectOldSpacesRoute,
  },
  {
    name: 'Space',
    path: '/community/:communityId/space/:spaceId',
    component: () => import('@/pages/Space.vue'),
    redirect: { name: 'SpaceDiscussions' },
    props: true,
    meta: { communityScope: true },
    children: [
      {
        name: 'SpaceDiscussions',
        path: 'discussions',
        component: () => import('@/pages/SpaceDiscussions.vue'),
        props: true,
        meta: { communityScope: true },
      },
      {
        name: 'SpacePages',
        path: 'pages',
        component: () => import('@/pages/SpacePages.vue'),
        props: true,
        meta: { communityScope: true },
      },
      {
        name: 'SpacePage',
        path: 'pages/:pageId/:slug?',
        component: () => import('@/pages/Page.vue'),
        props: true,
        meta: { hideHeader: true, communityScope: true },
      },
      {
        name: 'SpaceTasks',
        path: 'tasks',
        component: () => import('@/pages/SpaceTasks.vue'),
        props: true,
        meta: { communityScope: true },
      },
      {
        name: 'SpaceTask',
        path: 'tasks/:taskId',
        component: () => import('@/pages/Task.vue'),
        props: true,
        meta: { hideHeader: true, communityScope: true },
      },
    ],
  },
  {
    name: 'Discussion',
    path: '/community/:communityId/space/:spaceId/discussion/:postId/:slug?',
    component: () => import('@/pages/SpaceDiscussion.vue'),
    props: true,
    meta: { communityScope: true },
  },
  {
    name: 'NewDiscussion',
    path: '/community/:communityId/new-discussion',
    component: () => import('@/pages/NewDiscussion/NewDiscussion.vue'),
    meta: { communityScope: true },
  },
  {
    name: 'LegacyNewDiscussion',
    path: '/new-discussion',
    component: () => import('@/pages/NewDiscussion/NewDiscussion.vue'),
  },
  {
    name: 'NewSpace',
    path: '/community/:communityId/new-space',
    component: () => import('@/pages/NewSpace.vue'),
    props: true,
    meta: { communityScope: true },
  },
  {
    path: '/people/:personId',
    name: 'PersonProfile',
    component: () => import('@/pages/PersonProfile.vue'),
    props: true,
    beforeEnter(to) {
      if (to.name === 'PersonProfile') {
        return { name: 'PersonProfileProfile', params: to.params }
      }
    },
    children: [
      {
        name: 'PersonProfileProfile',
        path: '',
        component: () => import('@/pages/PersonProfileProfile.vue'),
      },
      {
        // The About tab is now a card in the profile grid.
        path: 'about',
        redirect: (to) => ({ name: 'PersonProfileProfile', params: to.params }),
      },
      {
        name: 'PersonProfilePosts',
        path: 'posts',
        component: () => import('@/pages/PersonProfilePosts.vue'),
      },
      {
        name: 'PersonProfileReplies',
        path: 'replies',
        component: () => import('@/pages/PersonProfileReplies.vue'),
      },
      {
        name: 'PersonProfileBookmarks',
        path: 'bookmarks',
        redirect: { name: 'Bookmarks' },
      },
    ],
  },
  {
    path: '/profile/customize',
    name: 'ProfileCustomize',
    component: () => import('@/pages/ProfileCustomize.vue'),
  },
  {
    path: '/notifications',
    name: 'Notifications',
    component: () => import('@/pages/Notifications.vue'),
  },
  {
    // Settings is an overlay: the URL changes to /settings/:tab but the dialog
    // renders above whatever page it was opened from (see settingsBackgroundPath
    // + the beforeEach short-circuit below). RouteGuard renders nothing because
    // App.vue swaps the router-view to the background page while we're here.
    path: '/settings',
    meta: { settingsOverlay: true },
    redirect: { name: 'SettingsTab', params: { tab: 'profile' } },
    children: [
      {
        // Nested route for a single community's spaces/members inside the
        // Communities tab, so it gets its own URL and "back" returns to the
        // communities list. `:view` defaults to spaces when omitted.
        path: 'communities/:communityId/:view(spaces|members)?',
        name: 'SettingsCommunity',
        component: RouteGuard,
        meta: { settingsOverlay: true },
      },
      {
        path: ':tab',
        name: 'SettingsTab',
        component: RouteGuard,
        meta: { settingsOverlay: true },
      },
    ],
  },
  {
    path: '/more',
    name: 'More',
    component: () => import('@/pages/MoreMenu.vue'),
  },
  // Keep old shared space links working while moving canonical URLs under `/community/:communityId/...`.
  {
    path: '/space/:spaceId',
    component: RouteGuard,
    async beforeEnter(to) {
      const space = await findSpace(routeParam(to.params.spaceId))

      if (!space?.team) {
        return { name: 'NotFound' }
      }

      return {
        name: 'Space',
        params: {
          communityId: space.team,
          spaceId: space.name,
        },
      }
    },
  },
  {
    path: '/space/:spaceId/discussions',
    component: RouteGuard,
    async beforeEnter(to) {
      const space = await findSpace(routeParam(to.params.spaceId))

      if (!space?.team) {
        return { name: 'NotFound' }
      }

      return {
        name: 'SpaceDiscussions',
        params: {
          communityId: space.team,
          spaceId: space.name,
        },
      }
    },
  },
  {
    path: '/space/:spaceId/pages',
    component: RouteGuard,
    async beforeEnter(to) {
      const space = await findSpace(routeParam(to.params.spaceId))

      if (!space?.team) {
        return { name: 'NotFound' }
      }

      return {
        name: 'SpacePages',
        params: {
          communityId: space.team,
          spaceId: space.name,
        },
        hash: to.hash,
      }
    },
  },
  {
    path: '/space/:spaceId/pages/:pageId/:slug?',
    component: RouteGuard,
    async beforeEnter(to) {
      const space = await findSpace(routeParam(to.params.spaceId))

      if (!space?.team) {
        return { name: 'NotFound' }
      }

      return {
        name: 'SpacePage',
        params: {
          communityId: space.team,
          spaceId: space.name,
          pageId: routeParam(to.params.pageId),
          slug: optionalRouteParam(to.params.slug),
        },
        query: to.query,
        hash: to.hash,
      }
    },
  },
  {
    path: '/space/:spaceId/tasks',
    component: RouteGuard,
    async beforeEnter(to) {
      const space = await findSpace(routeParam(to.params.spaceId))

      if (!space?.team) {
        return { name: 'NotFound' }
      }

      return {
        name: 'SpaceTasks',
        params: {
          communityId: space.team,
          spaceId: space.name,
        },
      }
    },
  },
  {
    path: '/space/:spaceId/tasks/:taskId',
    component: RouteGuard,
    async beforeEnter(to) {
      const space = await findSpace(routeParam(to.params.spaceId))

      if (!space?.team) {
        return { name: 'NotFound' }
      }

      return {
        name: 'SpaceTask',
        params: {
          communityId: space.team,
          spaceId: space.name,
          taskId: routeParam(to.params.taskId),
        },
        query: to.query,
      }
    },
  },
  {
    path: '/space/:spaceId/discussion/:postId/:slug?',
    component: RouteGuard,
    async beforeEnter(to) {
      const space = await findSpace(routeParam(to.params.spaceId))

      if (!space?.team) {
        return { name: 'NotFound' }
      }

      return {
        name: 'Discussion',
        params: {
          communityId: space.team,
          spaceId: space.name,
          postId: routeParam(to.params.postId),
          slug: optionalRouteParam(to.params.slug),
        },
        query: to.query,
        hash: to.hash,
      }
    },
  },
  {
    path: '/:teamId',
    name: 'TeamLayout',
    redirect: (to) => ({ name: 'Team', params: { teamId: routeParam(to.params.teamId) } }),
    props: true,
    children: [
      {
        name: 'Team',
        path: '',
        component: RouteGuard,
        props: true,
        beforeEnter: redirectLegacyTeamRoute,
      },
      {
        name: 'TeamDiscussions',
        path: 'discussions',
        component: RouteGuard,
        beforeEnter: redirectLegacyTeamRoute,
      },
      {
        name: 'ProjectLayout',
        path: 'projects/:projectId',
        props: true,
        redirect: { name: 'Project' },
        children: [
          {
            name: 'Project',
            path: '',
            redirect: { name: 'ProjectOverview' },
            props: true,
            children: [
              {
                name: 'ProjectOverview',
                path: '',
                redirect: (to) => ({
                  name: 'Space',
                  params: {
                    communityId: routeParam(to.params.teamId),
                    spaceId: routeParam(to.params.projectId),
                  },
                }),
              },
              {
                name: 'ProjectDiscussions',
                path: 'discussions',
                redirect: (to) => ({
                  name: 'SpaceDiscussions',
                  params: {
                    communityId: routeParam(to.params.teamId),
                    spaceId: routeParam(to.params.projectId),
                  },
                }),
              },
              {
                name: 'ProjectDiscussion',
                path: 'discussion/:postId/:slug?',
                redirect: (to) => ({
                  name: 'Discussion',
                  params: {
                    communityId: routeParam(to.params.teamId),
                    spaceId: routeParam(to.params.projectId),
                    postId: routeParam(to.params.postId),
                    slug: optionalRouteParam(to.params.slug),
                  },
                  query: to.query,
                  hash: to.hash,
                }),
              },
              {
                name: 'ProjectDiscussionNew',
                path: 'discussions/new',
                redirect: (to) => ({
                  name: 'NewDiscussion',
                  params: {
                    communityId: routeParam(to.params.teamId),
                  },
                  query: {
                    ...to.query,
                    spaceId: routeParam(to.params.projectId),
                  },
                }),
              },
              {
                name: 'ProjectTasks',
                path: 'tasks',
                redirect: (to) => ({
                  name: 'SpaceTasks',
                  params: {
                    communityId: routeParam(to.params.teamId),
                    spaceId: routeParam(to.params.projectId),
                  },
                }),
              },
              {
                name: 'ProjectTaskDetail',
                path: 'task/:taskId',
                meta: { fullWidth: true },
                redirect: (to) => ({
                  name: 'SpaceTask',
                  params: {
                    communityId: routeParam(to.params.teamId),
                    spaceId: routeParam(to.params.projectId),
                    taskId: routeParam(to.params.taskId),
                  },
                  query: to.query,
                }),
              },
              {
                name: 'ProjectPages',
                path: 'pages',
                redirect: (to) => ({
                  name: 'SpacePages',
                  params: {
                    communityId: routeParam(to.params.teamId),
                    spaceId: routeParam(to.params.projectId),
                  },
                  hash: to.hash,
                }),
              },
              {
                name: 'ProjectPage',
                path: 'pages/:pageId/:slug?',
                meta: { fullWidth: true, hideHeader: true },
                redirect: (to) => ({
                  name: 'SpacePage',
                  params: {
                    communityId: routeParam(to.params.teamId),
                    spaceId: routeParam(to.params.projectId),
                    pageId: routeParam(to.params.pageId),
                    slug: optionalRouteParam(to.params.slug),
                  },
                  query: to.query,
                  hash: to.hash,
                }),
              },
            ],
          },
        ],
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: { name: 'NotFound' },
  },
]

const router = createRouter({
  history: createWebHistory(__FRONTEND_ROUTE__ + '/'),
  routes,
})

const scrollPositions: Record<string, number> = {}

function saveAndRestoreScrollPosition(to: RouteLocationNormalized, from: RouteLocationNormalized) {
  let scrollContainer = getScrollContainer()
  if (scrollContainer) {
    scrollPositions[from.path] = scrollContainer.scrollTop
  }
  if (scrollPositions[to.path] !== undefined && to.path !== from.path) {
    setTimeout(() => {
      scrollTo({ top: scrollPositions[to.path] })
    }, 0)
  }
}

router.beforeEach(async (to, from) => {
  saveAndRestoreScrollPosition(to, from)

  if (to.name === 'Login' && session.isLoggedIn) {
    return { name: 'Home' }
  }

  if (to.name !== 'Login' && !session.isLoggedIn) {
    window.location.href = '/login'
    return { name: 'Login' }
  }

  // Wait only for the first load. Gating on `users.isFinished` would also block every
  // navigation behind a background reload of the user list (see `usersReady`).
  if (!usersReady.value) {
    try {
      await users.promise
    } catch (error) {
      console.error('Error loading users', error)
    }
  }

  await ensureCommunityDataLoaded()

  // Settings overlay: don't run the community-scope/canonical logic below, which
  // would tear down the page the dialog is layered over. Just remember which page
  // that is so App.vue can keep rendering it behind the dialog.
  if (to.matched.some((route) => route.meta?.settingsOverlay)) {
    const comingFromSettings = from.matched.some((route) => route.meta?.settingsOverlay)
    if (!comingFromSettings) {
      if (from.matched.length > 0) {
        // In-app open: layer over the page we came from (already scoped correctly).
        settingsBackgroundPath.value = from.fullPath
      } else {
        // Cold load / refresh on a /settings URL: default to Home and scope its
        // community so the background page can actually render.
        const home = getHomeRoute()
        const homeCommunityId =
          typeof home === 'object' && 'params' in home
            ? (home.params?.communityId as string | undefined)
            : undefined
        if (homeCommunityId) communityState.scope(homeCommunityId)
        settingsBackgroundPath.value = router.resolve(home).fullPath
      }
    }
    return
  }
  settingsBackgroundPath.value = null

  let isCommunityScopedRoute = to.matched.some((route) => route.meta?.communityScope)
  if (!isCommunityScopedRoute) {
    communityState.scope(null)
  }

  if (['/', '/community'].includes(to.path)) {
    return getHomeRoute()
  }

  const canonicalContentRoute = await getCanonicalContentRoute(to, from)
  if (canonicalContentRoute) {
    return canonicalContentRoute
  }

  if (!isCommunityScopedRoute) {
    return
  }

  let communityId = routeParam(to.params.communityId)

  let space = to.params.spaceId ? getSpace(routeParam(to.params.spaceId)) : null

  if (to.params.spaceId && !space) {
    if (isRouteValidationUnavailable()) {
      communityState.scope(communityId)
      return
    }
    return { name: 'NotFound' }
  }

  if (space?.team && space.team !== communityId) {
    return redirectCurrentRouteToCommunity(to, space.team)
  }

  let community = getCommunity(communityId)

  // Invalid community URLs should fail loudly instead of silently switching shell state.
  // Public communities are visible even when the user has not joined them, so route validity
  // cannot be tied to the active sidebar community list.
  if (!community) {
    if (isRouteValidationUnavailable()) {
      communityState.scope(communityId)
      return
    }
    return { name: 'NotFound' }
  }

  if (community.archived_at) {
    return { name: 'NotFound' }
  }

  communityState.scope(communityId)
})

export default router

async function ensureCommunityDataLoaded() {
  await Promise.all([waitForResource(communities), waitForResource(spaces)])
  // Right after a reload, navigator.onLine can briefly lag the browser's actual
  // network state, so isBrowserOffline() alone can miss a reload that's genuinely
  // offline. A resource that already finished with a network error is unambiguous
  // proof the fresh fetch can't be trusted, so treat either signal the same way:
  // give the IndexedDB cache a bounded chance to hydrate before the home route is
  // decided from (possibly still-empty) `communities`/`spaces` data.
  if (isNetworkUnreliable()) {
    await Promise.all([waitForOfflineCachedData(communities), waitForOfflineCachedData(spaces)])
  }
}

async function waitForResource(resource: ResourceLike) {
  if (resource?.isFinished) {
    return
  }

  await until(() => resource?.isFinished).toBe(true)
}

function waitForOfflineCachedData(resource: ResourceLike) {
  if (hasHydratedData(resource)) {
    return Promise.resolve()
  }

  return new Promise<void>((resolve) => {
    const timeout = window.setTimeout(done, OFFLINE_CACHE_HYDRATION_TIMEOUT)
    const stop = watch(
      () => resource.data,
      () => {
        if (hasHydratedData(resource)) {
          done()
        }
      },
    )

    function done() {
      window.clearTimeout(timeout)
      stop()
      resolve()
    }
  })
}

function hasHydratedData(resource: ResourceLike) {
  const data = resource.data
  return Array.isArray(data) ? data.length > 0 : data != null
}

function isRouteValidationUnavailable() {
  return isNetworkUnreliable()
}

function isNetworkUnreliable() {
  return isBrowserOffline() || hasNetworkError(communities) || hasNetworkError(spaces)
}

function hasNetworkError(resource: ResourceLike) {
  return Boolean(resource?.error && isNetworkError(resource.error))
}

export function getHomeRoute(): RouteLocationRaw {
  if (isMobileViewport() && communityState.id) {
    return { name: 'Home' }
  }

  return getDesktopHomeRoute()
}

function getDesktopHomeRoute(): RouteLocationRaw {
  // Home resolves to the active community when possible; onboarding stays only for truly empty sites.
  if (communityState.id) {
    return {
      name: 'Discussions',
      params: { communityId: communityState.id },
    }
  }

  if (!hasAnyData()) {
    return { name: 'Onboarding' }
  }

  // The site has communities/spaces but the user has joined none. Admins manage
  // them from the NoCommunities page (which opens the Communities settings tab).
  return { name: 'NoCommunities' }
}

function isMobileViewport() {
  return typeof window !== 'undefined' && window.innerWidth < 640
}

function hasAnyData(): boolean {
  return (communities.data?.length ?? 0) > 0 || (spaces.data?.length ?? 0) > 0
}

function redirectCurrentRouteToCommunity(to: RouteLocationNormalized, communityId: string) {
  return {
    name: to.name ?? 'Space',
    params: {
      ...to.params,
      communityId,
    },
    query: to.query,
    hash: to.hash,
    replace: true,
  }
}

async function getCanonicalContentRoute(
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
): Promise<RouteLocationRaw | undefined> {
  const descriptor = getContentRouteDescriptor(to)
  if (!descriptor) return

  const documentName = routeParam(to.params[descriptor.documentParam])
  if (!documentName) return

  // Fast path: in-app links (list rows, sidebar, command palette) already carry a fully
  // resolved community + space derived from local data, so a locally-valid space means the
  // URL is already canonical — skip the blocking server fetch and let the route change
  // immediately (the detail page shows its own skeleton). Restricted to in-app navigation:
  // deep links (first load, refresh, pasted or hand-edited URLs — from is START_LOCATION
  // with no matched records) still hit the server so a deleted document 404s and a stale
  // space/slug rewrites to canonical.
  const isInAppNavigation = from.matched.length > 0
  if (isInAppNavigation && hasCanonicalLocalParams(to, descriptor)) return
  if (isRouteValidationUnavailable() && hasCanonicalLocalParams(to, descriptor)) return
  if (isRouteValidationUnavailable()) return

  const doc = await getProjectContentDoc(descriptor.doctype, documentName)
  if (doc === undefined) {
    if (hasCanonicalLocalParams(to, descriptor)) return
    return
  }
  if (!doc?.project) return { name: 'NotFound' }

  const space = await findSpace(String(doc.project))
  if (!space?.team) return { name: 'NotFound' }

  const params: Record<string, RouteParamValue | undefined> = {
    ...to.params,
    communityId: space.team,
    spaceId: space.name,
  }
  if (descriptor.slugParam && doc.slug) {
    params[descriptor.slugParam] = doc.slug
  }

  if (isCurrentContentRoute(to, descriptor, params)) return

  return {
    name: descriptor.routeName,
    params,
    query: to.query,
    hash: to.hash,
    replace: true,
  }
}

function hasCanonicalLocalParams(
  to: RouteLocationNormalized,
  descriptor: ContentRouteDescriptor,
): boolean {
  if (to.name !== descriptor.routeName) return false

  const communityId = optionalRouteParam(to.params.communityId)
  const spaceId = optionalRouteParam(to.params.spaceId)
  if (!communityId || !spaceId) return false

  // A missing slug means the URL still needs canonicalizing to add it, so fall through.
  if (descriptor.slugParam && !optionalRouteParam(to.params.slug)) return false

  // The space must exist locally and belong to the community in the URL; otherwise the
  // link is stale or cross-community and needs the server to resolve the real mapping.
  const space = getSpace(spaceId)
  return Boolean(space?.team) && space?.team === communityId
}

function getContentRouteDescriptor(to: RouteLocationNormalized): ContentRouteDescriptor | null {
  if (to.params.postId) {
    return {
      doctype: 'GP Discussion',
      documentParam: 'postId',
      routeName: 'Discussion',
      slugParam: 'slug',
    }
  }
  if (to.params.pageId) {
    return {
      doctype: 'GP Page',
      documentParam: 'pageId',
      routeName: 'SpacePage',
      slugParam: 'slug',
    }
  }
  if (to.params.taskId) {
    return {
      doctype: 'GP Task',
      documentParam: 'taskId',
      routeName: 'SpaceTask',
    }
  }
  return null
}

async function getProjectContentDoc(doctype: ContentRouteDescriptor['doctype'], name: string) {
  const cacheKey = `${doctype}:${name}`
  const cachedRequest = projectContentDocRequests.get(cacheKey)
  if (cachedRequest) return cachedRequest

  const request = fetchProjectContentDoc(doctype, name)
  projectContentDocRequests.set(cacheKey, request)
  request.finally(() => {
    window.setTimeout(() => projectContentDocRequests.delete(cacheKey), 1000)
  })
  return request
}

async function fetchProjectContentDoc(doctype: ContentRouteDescriptor['doctype'], name: string) {
  try {
    return await call<ProjectContentDoc>('frappe.client.get', { doctype, name })
  } catch (error) {
    if (isNetworkError(error)) return undefined
    return null
  }
}

function isCurrentContentRoute(
  to: RouteLocationNormalized,
  descriptor: ContentRouteDescriptor,
  params: Record<string, RouteParamValue | undefined>,
) {
  if (to.name !== descriptor.routeName) return false
  if (routeParam(to.params.communityId) !== params.communityId) return false
  if (routeParam(to.params.spaceId) !== params.spaceId) return false

  if (descriptor.slugParam && params.slug) {
    return optionalRouteParam(to.params.slug) === params.slug
  }

  return true
}

async function findSpace(spaceId: string): Promise<Space | null> {
  await ensureCommunityDataLoaded()
  return getSpace(spaceId)
}
