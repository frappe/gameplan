import { createRouter, createWebHistory } from 'vue-router'
import { session } from './data/session'
import { users } from './data/users'

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
    path: '/home',
    name: 'Home',
    component: () => import('@/pages/Home.vue'),
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
    name: 'Team',
    component: () => import('@/pages/Team.vue'),
    redirect: { name: 'TeamHome' },
    props: true,
    children: [
      {
        name: 'TeamHome',
        path: '',
        component: () => import('@/pages/TeamHome.vue'),
        redirect: { name: 'TeamOverview' },
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
        ],
      },
      {
        name: 'Project',
        path: 'projects/:projectId',
        component: () => import('@/pages/Project.vue'),
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
            name: 'ProjectDiscussion',
            path: 'discussion/:postId',
            component: () => import('@/pages/ProjectDiscussion.vue'),
            props: true,
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
    ],
  },
]

let router = createRouter({
  history: createWebHistory('/g/'),
  routes,
})

let scrollPositions = {}
function saveAndRestoreScrollPosition(to, from) {
  // window.scrollContainer is reference to the scroll container in AppLayout.vue
  if (window.scrollContainer) {
    scrollPositions[from.fullPath] = window.scrollContainer.scrollTop
  }
  if (scrollPositions[to.fullPath] !== undefined) {
    setTimeout(() => {
      window.scrollContainer.scrollTop = scrollPositions[to.fullPath]
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
