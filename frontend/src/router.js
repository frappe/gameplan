import { createRouter, createWebHistory } from 'vue-router'
import { session } from './data/session'
import { users } from './data/users'
import { getScrollContainer, scrollTo } from './utils/scrollContainer'

let defaultRoute = window.default_route
if (defaultRoute?.includes('{{')) {
  defaultRoute = '/home'
}

const routes = [
  {
    path: '/',
    redirect: defaultRoute,
  },
  {
    path: '/home/:feedType?',
    name: 'Home',
    component: () => import('@/pages/Home.vue'),
    props: true,
    beforeEnter: (to, from, next) => {
      if (!to.params.feedType) {
        next({ name: 'Home', params: { feedType: 'recent' } })
      } else {
        next()
      }
    },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/Login.vue'),
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
  },
  {
    path: '/list',
    name: 'Teams',
    component: () => import('@/pages/Teams.vue'),
  },
  {
    path: '/people/:personId',
    name: 'PersonProfile',
    component: () => import('@/pages/PersonProfile.vue'),
    props: true,
    redirect: { name: 'PersonProfileAboutMe' },
    children: [
      {
        name: 'PersonProfileAboutMe',
        path: '',
        component: () => import('@/pages/PersonProfileAboutMe.vue'),
      },
      {
        name: 'PersonProfilePosts',
        path: 'posts',
        component: () => import('@/pages/PersonProfilePosts.vue'),
      },
    ],
  },
  {
    path: '/notifications',
    name: 'Notifications',
    component: () => import('@/pages/Notifications.vue'),
  },
  {
    path: '/:teamId',
    name: 'TeamLayout',
    component: () => import('@/pages/TeamLayout.vue'),
    redirect: { name: 'Team' },
    props: true,
    children: [
      {
        name: 'Team',
        path: '',
        component: () => import('@/pages/Team.vue'),
        redirect: { name: 'TeamProjects' },
        props: true,
        children: [
          {
            name: 'TeamOverview',
            path: 'overview',
            component: () => import('@/pages/TeamOverview.vue'),
          },
          {
            name: 'TeamProjects',
            path: 'projects',
            component: () => import('@/pages/TeamProjects.vue'),
          },
          {
            name: 'TeamDiscussions',
            path: 'discussions',
            component: () => import('@/pages/TeamDiscussions.vue'),
          },
        ],
      },
      {
        name: 'ProjectLayout',
        path: 'projects/:projectId',
        component: () => import('@/pages/ProjectLayout.vue'),
        props: true,
        redirect: { name: 'Project' },
        children: [
          {
            name: 'Project',
            path: '',
            component: () => import('@/pages/Project.vue'),
            redirect: { name: 'ProjectDiscussions' },
            props: true,
            children: [
              {
                name: 'ProjectOverview',
                path: '',
                component: () => import('@/pages/ProjectOverview.vue'),
              },
              {
                name: 'ProjectDiscussions',
                path: 'discussions',
                component: () => import('@/pages/ProjectDiscussions.vue'),
              },
              {
                name: 'ProjectDiscussionNew',
                path: 'discussions/new',
                component: () => import('@/pages/ProjectDiscussionNew.vue'),
              },
              {
                name: 'ProjectTasks',
                path: 'tasks',
                component: () => import('@/pages/ProjectTasks.vue'),
              },
              {
                name: 'ProjectTaskNew',
                path: 'tasks/new',
                component: () => import('@/pages/ProjectTaskNew.vue'),
              },
              {
                name: 'ProjectTaskDetail',
                path: 'tasks/:taskId',
                component: () => import('@/pages/ProjectTaskDetail.vue'),
                props: true,
              },
            ],
          },
          {
            name: 'ProjectDiscussion',
            path: 'discussion/:postId/:slug?',
            component: () => import('@/pages/ProjectDiscussion.vue'),
            props: true,
          },
        ],
      },
    ],
  },
]

let router = createRouter({
  history: createWebHistory('/g/'),
  routes,
})

let scrollPositions = {}
function saveAndRestoreScrollPosition(to, from) {
  let scrollContainer = getScrollContainer()
  if (scrollContainer) {
    scrollPositions[from.fullPath] = scrollContainer.scrollTop
  }
  if (scrollPositions[to.fullPath] !== undefined) {
    setTimeout(() => {
      scrollTo({ top: scrollPositions[to.fullPath] })
    }, 0)
  }
}

router.beforeEach(async (to, from, next) => {
  saveAndRestoreScrollPosition(to, from)
  let isLoggedIn = session.isLoggedIn
  try {
    await users.promise
  } catch (error) {
    isLoggedIn = false
  }

  if (to.name === 'Login' && isLoggedIn) {
    next({ name: 'Home' })
  } else if (to.name !== 'Login' && !isLoggedIn) {
    next({ name: 'Login' })
  } else {
    next()
  }
})

export default router
