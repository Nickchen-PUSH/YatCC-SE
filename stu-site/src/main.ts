import { createApp } from 'vue'
import 'element-plus/theme-chalk/dark/css-vars.css'
import '@/assets/style.css'
import App from '@/App.vue'

import 'virtual:uno.css'
import router from './routes'

function initApp() {
  const app = createApp(App)

  app.use(router)

  app.mount('#app')
}

if (import.meta.env.MODE === 'development' && import.meta.env.VITE_MOCK === 'true') {
  const { worker } = await import('@/mocks/browser')
  worker
    .start({
      serviceWorker: {
        url: '/static/mockServiceWorker.js',
      },
    })
    .then(() => {
      initApp()
    })
} else {
  initApp()
}
