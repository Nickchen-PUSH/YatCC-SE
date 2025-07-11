import type { ResourceCreation, ResourceDeletion } from '@/types/api'
import request from './base'
import type { Task } from '@/types'

type TaskerInfo = Task & {
  when: number
}

// 批量添加任务
export async function addTasks(taskinfos: TaskerInfo[]): Promise<ResourceCreation | null> {
  const response = await request({
    route: 'task',
    method: 'POST',
    data: taskinfos,
  })
  if (!response || response.status === 202) {
    return null
  } else {
    return response.json()
  }
}

// 获取任务详情
export async function getTaskDetail(id: number): Promise<Task | null> {
  const response = await request({
    route: `task/${id}`,
    method: 'GET',
  })
  if (!response || response.status === 202) {
    return null
  } else {
    return response.json()
  }
}

// 批量删除任务
export async function deleteTasks(ids: number[]): Promise<ResourceDeletion | null> {
  const response = await request({
    route: `task`,
    method: 'DELETE',
    data: ids,
  })
  if (!response || response.status === 202) {
    return null
  } else {
    return response.json()
  }
}

type TaskBrief = {
  when: number // 计划时间（UNIX 时间戳）
  id: number // 任务 ID
  desc: string // 任务描述
  cmd: string // 命令
  cwd: string | null // 工作目录
  is_resumable: boolean // 是否应在服务器重启后继续执行
  is_routine: boolean // 是否是循环例程
}

// 获取任务列表
export async function getTaskList(page: number, pageSize: number): Promise<TaskBrief[] | null> {
  const response = await request({
    route: `task?page=${page}&size=${pageSize}`,
    method: 'GET',
  })
  if (!response) {
    return null
  }
  if (!response || response.status === 202) {
    return null
  } else {
    return response.json()
  }
}
