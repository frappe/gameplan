import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/pages/Home.vue'),
  },
  {
    path: '/:id',
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
        props: true
      },
    ],
  },
]

let router = createRouter({
  history: createWebHistory('/teams/'),
  routes,
})

export default router
