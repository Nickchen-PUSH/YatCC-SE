import type { ResourceCreation, ResourceDeletion } from '@/types/api'
import request from './base'
import { type StudentBrief, type StudentDetailInfo, type StudentInfo } from '@/types'

// 获取学生信息
export async function getStudentDetail(id: string): Promise<StudentDetailInfo | null> {
  const response = await request({
    route: `student/${id}`,
    method: 'GET',
  })
  if (!response) {
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
  time_quota: number
}

// 批量添加学生
export async function addStudents(
  students: StudentCreationParams[],
): Promise<ResourceDeletion | null> {
  const response = await request({
    route: `student`,
    method: 'POST',
    data: students,
  })
  if (!response) {
    return null
  } else {
    return response.json()
  }
}


// 批量删除学生
export async function deleteStudents(
  ids: string[],
): Promise<ResourceDeletion | null> {
  const response = await request({
    route: `student`,
    method: 'DELETE',
    data: ids,
  })
  if (!response) {
    return null
  } else {
    return response.json()
  }
}


// 获取学生列表
export async function getStudentList(

): Promise<{ students: StudentBrief[] } | null> {
  const response = await request({
    route: `student`,
    method: 'GET',
  })
  if (!response) {
    return null
  }
else {
    const students: StudentBrief[] = await response.json()
    return { students }
  }
}


