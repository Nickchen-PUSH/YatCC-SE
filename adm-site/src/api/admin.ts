import { clearAPIKEY, setAPIKEY } from './auth'
import request from './base'

// 验证 API KEY
export async function authAdmin(apikey: string): Promise<'Ok' | 'Failed' | 'Error'> {
  setAPIKEY(apikey)
  const response = await request({
    route: 'api-key',
    method: 'GET',
    igoreAuthFailed: true,
  })
  if (!response) {
    clearAPIKEY()
    return 'Error'
  }
  switch (response.status) {
    case 201:
      return 'Ok'
    case 202:
      clearAPIKEY()
      return 'Failed'
    default:
      clearAPIKEY()
      return 'Error'
  }
}

// 获取 API KEY（一般不会用到）
export async function getAdminAPIkey(): Promise<string | null> {
  const response = await request({
    route: 'api-key',
    method: 'GET',
  })
  if (!response) {
    return null
  }
  switch (response.status) {
    case 201:
      return response.text()
    default:
      return null
  }
}

// 设置 API KEY
export async function setAdminAPIkey(new_apikey: string): Promise<'Ok' | 'Failed' | 'Error'> {
  const response = await request({
    route: 'api-key',
    method: 'PUT',
    data: JSON.stringify(new_apikey),
  })
  if (!response) {
    return 'Error'
  }
  switch (response.status) {
    case 201:
      return 'Ok'
    case 202:
      return 'Failed'
    default:
      return 'Error'
  }
}

// 暂时未实现
export async function getAdminMails(): Promise<string[]> {
  return []
}

// 暂时未实现
export async function addAdminMail(mail: string): Promise<'Ok' | 'Failed'> {
  return 'Failed'
}

// 暂时未实现
export async function removeAdminMail(mail: string): Promise<'Ok' | 'Failed'> {
  return 'Failed'
}
