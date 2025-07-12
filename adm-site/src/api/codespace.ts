import type { ResourceDeletion } from '@/types/api'
import request from './base'



// 批量启动学生的代码空间
export async function startCodespaces(ids: string[]): Promise<ResourceDeletion | null> {
  const response = await request({
    route: 'student/codespace',
    method: 'POST',
    data: ids,
  })
  if (!response) {
    return null
  }
  switch (response.status) {
    case 200:
      return response.json()
    default:
      return null
  }
}

// 批量停止学生的代码空间
export async function stopCodespaces(sids: string[]): Promise<ResourceDeletion | null> {
  const response = await request({
    route: 'student/codespace',
    method: 'DELETE',
    data: sids,
  })
  if (!response) {
    return null
  }
  switch (response.status) {
    case 200:
      return response.json()
    default:
      return null
  }
}
