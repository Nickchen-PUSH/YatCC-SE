import { setToken } from '@/composables/auth'
import request from './base'

// 登录账户
export async function login(sid: string, pwd: string): Promise<'Ok' | 'Failed' | 'Error'> {
  const response = await request({
    route: 'login',
    method: 'POST',
    data: { sid, pwd },
    auth: false,
  })
  if (!response) {
    return 'Error'
  }
  if (response.status === 200) {
    const api_key = await response.text()
    setToken(api_key)
    return 'Ok'
  } else {
    return 'Failed'
  }
}
