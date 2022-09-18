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
    name: 'TeamPage',
    component: () => import('@/pages/TeamPage.vue'),
    props: true,
    children: [
      {
        name: 'TeamPageHome',
        path: '',
        component: () => import('@/pages/TeamPageHome.vue'),
      },
      {
        name: 'ProjectDetail',
        path: 'projects/:projectId',
        component: () => import('@/pages/ProjectDetail.vue'),
        props: true,
        children: [
          {
            name: 'ProjectDetailOverview',
            path: '',
            component: () => import('@/pages/ProjectDetailOverview.vue'),
          },
          {
            name: 'ProjectDetailDiscussions',
            path: 'discussions',
            component: () => import('@/pages/ProjectDetailDiscussions.vue'),
          },
          {
            name: 'ProjectDetailDiscussionNew',
            path: 'discussions/new',
            component: () => import('@/pages/ProjectDetailDiscussionNew.vue'),
          },
          {
            name: 'ProjectDetailDiscussion',
            path: 'discussion/:postId',
            component: () => import('@/pages/ProjectDetailDiscussion.vue'),
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
