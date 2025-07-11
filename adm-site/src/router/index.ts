import { createRouter, createWebHashHistory } from 'vue-router'
import { isAuthenticated } from '../api/auth'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      children: [
        {
          path: '',
          redirect: '/student-list',
        },
        {
          path: 'student-list',
          component: () => import('@/components/home/student/StudentList/StudentList.vue'),
        },
        {
          path: 'student-add',
          component: () => import('@/components/home/student/StudentAdd/StudentAdd.vue'),
        },
        {
          path: 'tasker',
          component: () => import('@/components/home/tasker/TaskerList.vue'),
        },
        {
          path: 'codespace',
          component: () => import('@/components/home/codespace/CodespaceList.vue'),
        },
        {
          path: 'account',
          component: () => import('@/components/home/account/AccountPanel.vue'),
        },

      ],
    },

  ],
})

export default router
