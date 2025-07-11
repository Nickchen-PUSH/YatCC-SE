import { ElMessageBox, type Action } from 'element-plus'
import router from '@/router'

function isAuthenticated() {
  return localStorage.getItem('apikey') !== null
}

function setAPIKEY(token: string) {
  localStorage.setItem('apikey', token)
}

function getAPIKEY() {
  return localStorage.getItem('apikey')
}

function clearAPIKEY() {
  localStorage.removeItem('apikey')
}

function handleUnauthorized() {
  ElMessageBox.alert('APIKEY无效,请设置', '', {
    confirmButtonText: '确定',
    callback: (_: Action) => {
      router.push('/account')
    },
  },
)
}

export { isAuthenticated, setAPIKEY, getAPIKEY, clearAPIKEY, handleUnauthorized }
