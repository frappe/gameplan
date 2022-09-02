import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/home',
  },
  {
    path: '/daily-planner/:date?',
    name: 'DailyPlanner',
    component: () => import('@/pages/DailyPlanner.vue'),
    props: true,
    children: [
      {
        name: 'DailyPlannerNotes',
        path: 'notes',
        component: () => import('@/pages/DailyPlannerNotes.vue'),
      },
      {
        name: 'DailyPlannerTasks',
        path: 'tasks',
        component: () => import('@/pages/DailyPlannerTasks.vue'),
      },
      {
        name: 'DailyPlannerCalendar',
        path: 'calendar',
        component: () => import('@/pages/DailyPlannerCalendar.vue'),
      },
    ],
  },
  {
    path: '/inbox',
    name: 'Inbox',
    component: () => import('@/pages/ComingSoon.vue'),
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('@/pages/Tasks.vue'),
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
    path: '/people/:personId',
    name: 'PersonProfile',
    component: () => import('@/pages/PersonProfile.vue'),
    props: true,
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
      {
        name: 'TeamPageDocuments',
        path: 'documents',
        component: () => import('@/pages/TeamPageDocuments.vue'),
      },
      {
        path: 'document/:documentId/edit',
        name: 'EditDocument',
        component: () => import('@/pages/EditDocument.vue'),
        props: true,
      },
    ],
  },
]

let router = createRouter({
  history: createWebHistory('/teams/'),
  routes,
})

router.beforeEach(() => {
  // window.scrollTo(0, 0)
})

export default router
