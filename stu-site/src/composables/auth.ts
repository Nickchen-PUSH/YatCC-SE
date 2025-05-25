import router from "@/routes"
import type { Action } from "element-plus"

export function isAuthenticated() {
  return localStorage.getItem('token') !== null
}

export function clearToken() {
  localStorage.removeItem('token')
}

export function setToken(token: string) {
  localStorage.setItem('token', token)
}

export function getToken() {
  return localStorage.getItem('token')
}

export function handleUnauthorized(){
  ElMessageBox.alert('登录状态无效', '', {
    confirmButtonText: '确定',
    callback: (_: Action) => {
      if (isAuthenticated()) {
        clearToken()
      }
      router.push('/login')
    },
  })
}
