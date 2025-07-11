import { http, HttpResponse } from 'msw'
import { students } from './data/students'
import type { StudentInfo } from '@/types'
import type { StudentCreationParams } from '@/api/student'

export const handlers = [


  // 批量启动学生代码空间：POST student/codespace
  http.post(import.meta.env.VITE_API_URL + 'student/codespace', async ({ request }) => {
    const body = await request.json() as string[]
    const success: string[] = []
    const failed: { id: string; reason: string }[] = []
    console.log('body', body)
    console.log('students', students)
    for (const id of body) {
      const stu = students.find((s) => s.id === id)
      console.log('stu', stu)
      if (!stu) {
        failed.push({ id, reason: '学生不存在' })
      } else if (stu.url) {
        failed.push({ id, reason: '代码空间已启动' })
      } else {
        stu.url = `http://example.com/${id}`
        success.push(id)
      }
    }

    return HttpResponse.json({ success, failed })
  }),
  // 批量停止学生代码空间：DELETE /student/codespace
  http.delete(import.meta.env.VITE_API_URL + 'student/codespace', async ({ request }) => {
    const body = await request.json() as string[]
    const success: string[] = []
    const failed: { id: string; reason: string }[] = []

    for (const id of body) {
      const stu = students.find((s) => s.id === id)
      if (!stu) {
        failed.push({ id, reason: '学生不存在' })
      } else if (!stu.url) {
        failed.push({ id, reason: '代码空间未启动' })
      } else {
        stu.url = ''
        success.push(id)
      }
    }

    return HttpResponse.json({ success, failed })
  }),
  // 获取学生信息
  http.get(import.meta.env.VITE_API_URL + 'student/*', (info) => {
    const id = info.request.url.split('/').pop() as string
    const index = students.findIndex((stu) => stu.id === id)
    return HttpResponse.json(students[index])
  }),
  // 批量创建学生
  http.post(import.meta.env.VITE_API_URL + 'student', async (info) => {
    const body = (await info.request.json()) as StudentCreationParams[]
    const res = []
    for (let i = 0; i < body.length; i++) {
      if (students.some((stu) => stu.id === body[i].id)) {
        res[i] = false
      } else {
        students.push({
          ...body[i],
          is_synced: true,
          url: '',
          job: null,
          space_quota: 0,
          space_used: 0,
          time_used: 0,
        })
        res[i] = true
      }
    }
    return HttpResponse.json(res)
  }),

  // 批量删除学生
  http.delete(import.meta.env.VITE_API_URL + 'student', async (info) => {
    const body = (await info.request.json()) as string[]
    const res = Array.from({ length: body.length }).fill(false)
    for (let i = students.length - 1; i >= 0; i--) {
      if (body.includes(students[i].id)) {
        res[body.indexOf(students[i].id)] = true
        students.splice(i, 1)
      }
    }
    return HttpResponse.json(res)
  }),
  // 获取学生列表
  http.get(import.meta.env.VITE_API_URL + 'student', async ({ request }) => {

    const res = students.slice(0 , 5)
    return HttpResponse.json(res)
  }),

  // 批量添加任务

  // 获取任务详情
]
