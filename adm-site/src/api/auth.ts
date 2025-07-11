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
  ElMessageBox.alert('登录过期，请重新登录', '', {
    confirmButtonText: '确定',
    callback: (action: Action) => {
      router.push('/auth')
    },
  })
}

export { isAuthenticated, setAPIKEY, getAPIKEY, clearAPIKEY, handleUnauthorized }
