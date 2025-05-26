import type { ErrorResponse } from '@/types/api'
import request from './base'
import { type CodeSpaceInfo } from '@/types'

type CodeSpaceInfoResponse = {
  access_url: string | boolean
  last_start: number
  last_stop: number
  space_quota: number
  space_used: number
  time_quota: number
  time_used: number
}

// 获取代码空间信息
export async function getCodespaceInfo(): Promise<CodeSpaceInfo | null> {
  const response = await request({
    route: 'codespace/info',
    method: 'GET',
  })
  if (!response) {
    return null
  }
  if (response.status === 201) {
    const data: CodeSpaceInfoResponse = await response.json()
    return {
      access_url: data.access_url,
      last_start: new Date(data.last_start),
      last_stop: new Date(data.last_stop),
      space_quota: data.space_quota,
      space_used: data.space_used,
      time_quota: data.time_quota,
      time_used: data.time_used,
    }
  } else {
    return null
  }
}

// 启动代码空间
export async function startCodespace(): Promise<
  'Ok' | 'Already Running' | 'Run Out of Quota' | 'Error'
> {
  const response = await request({
    route: 'codespace',
    method: 'POST',
  })
  if (!response) {
    return 'Error'
  }
  if (response.status === 201) {
    return 'Ok'
  } else if (response.status === 202) {
    const error = (await response.json()) as ErrorResponse
    if (error.type === 1) {
      return 'Already Running'
    } else if (error.type === 2) {
      return 'Run Out of Quota'
    }
  }
  return 'Error'
}

// 停止代码空间
export async function stopCodespace(): Promise<'Ok' | 'Not Running' | 'Error'> {
  const response = await request({
    route: 'codespace',
    method: 'DELETE',
  })
  if (!response) {
    return 'Error'
  }
  if (response.status === 201) {
    return 'Ok'
  } else {
    return 'Not Running'
  }
}
