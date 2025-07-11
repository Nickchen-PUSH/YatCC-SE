import request from './base'
import { type UserInfo } from '@/types'
// 获取用户信息
export async function getUserInfo(): Promise<UserInfo | null> {
  const response = await request({
    route: 'user',
    method: 'GET',
  })
  if (!response) {
    return null
  }
  if (response.status === 200) {
    const data = await response.json()
    return data as UserInfo
  } else {
    return null
  }
}

// 重置密码
export async function resetPassword(
  oldPwd: string,
  newPwd: string,
): Promise<'Ok' | 'Failed' | 'Error'> {
  const response = await request({
    route: 'user',
    method: 'PATCH',
    data: { old_pwd: oldPwd, new_pwd: newPwd },
  })
  if (!response) {
    return 'Error'
  }
  if (response.status === 200) {
    return 'Ok'
  } else {
    return 'Failed'
  }
}

// 修改用户信息
export async function updateUserInfo(userInfo: UserInfo): Promise<'Ok' | 'Failed' | 'Error'> {
  const response = await request({
    route: 'user',
    method: 'PUT',
    data: userInfo,
  })
  if (!response) {
    return 'Error'
  }
  if (response.status === 200) {
    return 'Ok'
  } else {
    return 'Failed'
  }
}
