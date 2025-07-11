import type { ResourceCreation, ResourceDeletion } from '@/types/api'
import request from './base'
import { type StudentBrief, type StudentDetailInfo, type StudentInfo } from '@/types'

// 获取学生信息
export async function getStudentDetail(id: string): Promise<StudentDetailInfo | null> {
  const response = await request({
    route: `student/${id}`,
    method: 'GET',
  })
  if (!response || response.status === 202) {
    return null
  } else {
    return response.json()
  }
}

export type StudentCreationParams = {
  id: string
  mail: string
  name: string
  pwd: string
  space_quota: number
  time_quota: number
}

// 批量添加学生
export async function addStudents(
  students: StudentCreationParams[],
  force: boolean = false,
): Promise<ResourceDeletion | null> {
  const response = await request({
    route: `student?force=${force}`,
    method: 'POST',
    data: students,
  })
  if (!response || response.status === 202) {
    return null
  } else {
    return response.json()
  }
}

// 修改学生信息
export async function updateStudent(id: string, info: StudentInfo): Promise<'Ok' | 'Failed'> {
  const response = await request({
    route: `student/${id}`,
    method: 'PUT',
    data: info,
  })
  if (!response || response.status === 202) {
    return 'Failed'
  } else {
    return 'Ok'
  }
}

// 修改学生密码
export async function resetStudentPassword(sid: string, newPwd: string): Promise<'Ok' | 'Failed'> {
  const response = await request({
    route: `student/${sid}/pwd`,
    method: 'PUT',
    data: JSON.stringify(newPwd),
  })
  if (!response || response.status === 202) {
    return 'Failed'
  } else {
    return 'Ok'
  }
}

// 批量删除学生
export async function deleteStudents(
  ids: string[],
  force: boolean = false,
): Promise<ResourceDeletion | null> {
  const response = await request({
    route: `student?force=${force}`,
    method: 'DELETE',
    data: ids,
  })
  if (!response || response.status === 202) {
    return null
  } else {
    return response.json()
  }
}

type StudentListResponse = {
  total: number
  students: StudentBrief[]
}

// 获取学生列表
export async function getStudentList(
  page: number,
  size: number,
): Promise<StudentListResponse | null> {
  const response = await request({
    route: `student?page=${page}&size=${size}`,
    method: 'GET',
  })
  if (!response) {
    return null
  }
  if (response.status === 202) {
    return null
  } else {
    const students: StudentBrief[] = await response.json()
    const total = response.headers.get('yatcc-page-total') || '0'
    return { total: parseInt(total), students }
  }
}

export type IncreaseQuotaParams = {
  sid: string
  space_quota: number
  time_quota: number
}[]

export async function increaseQuota(params: IncreaseQuotaParams): Promise<ResourceCreation | null> {
  const response = await request({
    route: 'increase-quota',
    method: 'PUT',
    data: params,
  })
  if (!response || response.status === 202) {
    return null
  } else {
    return response.json()
  }
}
