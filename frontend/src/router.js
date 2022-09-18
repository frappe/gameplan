import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/home',
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/pages/Home.vue'),
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
  history: createWebHistory('/teams/'),
  routes,
})

export default router
