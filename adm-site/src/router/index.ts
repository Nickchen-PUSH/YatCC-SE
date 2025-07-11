import { createRouter, createWebHashHistory } from 'vue-router'
import { isAuthenticated } from '../api/auth'
import HomeView from '../views/HomeView.vue'
import AuthView from '../views/AuthView.vue'

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
        {
          path: 'notification',
          component: () => import('@/components/home/notification/NotifyPanel.vue'),
        },
      ],
    },
    {
      path: '/auth',
      name: 'auth',
      component: AuthView,
    },
  ],
})

router.beforeEach((to) => {
  if (
    // 检查用户是否已登录
    !isAuthenticated() &&
    // 避免无限重定向
    to.name !== 'auth'
  ) {
    // 将用户重定向到登录页面
    return { name: 'auth' }
  }
})

router.onError((error) => {
  if (error.name === 'UnauthorizedError') {
    // TODO: 使用更友好的提示信息替代 alert
    alert('认证状态过期，请重新认证')
    router.push('/auth')
  }
})

export default router
