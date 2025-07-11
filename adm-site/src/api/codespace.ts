import type { ResourceDeletion } from '@/types/api'
import request from './base'

// 批量清除学生的代码空间死状态
export async function clearDeadState(sids: string[]): Promise<ResourceDeletion | null> {
  const response = await request({
    route: 'codespace/clear-deadstate',
    method: 'PATCH',
    data: sids,
  })
  if (!response) {
    return null
  }
  switch (response.status) {
    case 201:
      return response.json()
    default:
      return null
  }
}

// 批量启动学生的代码空间
export async function startCodespaces(sids: string[]): Promise<ResourceDeletion | null> {
  const response = await request({
    route: 'codespace/start',
    method: 'PATCH',
    data: sids,
  })
  if (!response) {
    return null
  }
  switch (response.status) {
    case 201:
      return response.json()
    default:
      return null
  }
}

// 批量停止学生的代码空间
export async function stopCodespaces(sids: string[]): Promise<ResourceDeletion | null> {
  const response = await request({
    route: 'codespace/stop',
    method: 'PATCH',
    data: sids,
  })
  if (!response) {
    return null
  }
  switch (response.status) {
    case 201:
      return response.json()
    default:
      return null
  }
}
