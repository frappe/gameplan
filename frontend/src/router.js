import { createRouter, createWebHistory } from 'vue-router'
import { session } from './data/session'
import { users } from './data/users'
import { getScrollContainer, scrollTo } from './utils/scrollContainer'

let defaultRoute = window.default_route
if (defaultRoute?.includes('{{')) {
  defaultRoute = '/discussions'
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
    redirect: { name: 'Discussions' },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/Login.vue'),
  },
  {
    name: 'Discussions',
    path: '/discussions',
    component: () => import('@/pages/Discussions.vue'),
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
      {
        name: 'PersonProfileReplies',
        path: 'replies',
        component: () => import('@/pages/PersonProfileReplies.vue'),
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
        redirect: { name: 'TeamOverview' },
        props: true,
        children: [
          {
            name: 'TeamOverview',
            path: '',
            component: () => import('@/pages/TeamOverview.vue'),
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
            redirect: { name: 'ProjectOverview' },
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
                name: 'ProjectDiscussion',
                path: 'discussion/:postId/:slug?',
                component: () => import('@/pages/ProjectDiscussion.vue'),
                props: true,
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
                props: true,
              },
              {
                name: 'ProjectTaskDetail',
                path: 'task/:taskId',
                component: () => import('@/pages/ProjectTaskDetail.vue'),
                props: true,
                meta: { fullWidth: true },
              },
              {
                name: 'ProjectPages',
                path: 'pages',
                component: () => import('@/pages/ProjectPages.vue'),
              },
              {
                name: 'ProjectPage',
                path: 'pages/:pageId/:slug?',
                component: () => import('@/pages/Page.vue'),
                props: true,
                meta: { fullWidth: true, hideHeader: true },
              },
            ],
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
    scrollPositions[from.path] = scrollContainer.scrollTop
  }
  if (scrollPositions[to.path] !== undefined && to.path !== from.path) {
    setTimeout(() => {
      scrollTo({ top: scrollPositions[to.path] })
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
