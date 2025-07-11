import './assets/main.css'
import 'element-plus/theme-chalk/dark/css-vars.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

if (import.meta.env.MODE === 'development' && import.meta.env.VITE_MOCK === 'true') {
  const { worker } = await import('@/mocks/browser')
  worker.start({
    serviceWorker: {
      url: '/static/mockServiceWorker.js',
    },
  })
}

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
