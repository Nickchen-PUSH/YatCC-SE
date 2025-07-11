import { http, HttpResponse } from 'msw'
import { students } from './data/students'
import type { StudentInfo } from '@/types'
import type { IncreaseQuotaParams, StudentCreationParams } from '@/api/student'

export const handlers = [
  // 获取 API KEY
  http.get(import.meta.env.VITE_API_URL + 'api-key', () => {
    return new HttpResponse('apikey', {
      status: 201,
    })
  }),
  // 设置 API KEY
  http.put(import.meta.env.VITE_API_URL + 'api-key', () => {
    return new HttpResponse('成功', {
      status: 201,
    })
  }),
  // 批量清除学生的代码空间死状态
  http.patch(import.meta.env.VITE_API_URL + 'codespace/clear-deadState', async (info) => {
    const body = (await info.request.json()) as string[]
    const res = Array.from({ length: body.length }).fill(true)
    for (const id of body) {
      const index = students.findIndex((stu) => stu.id === id)
      if (index !== -1) {
        students[index].is_synced = true
      }
    }
    return HttpResponse.json(res, { status: 201 })
  }),
  // 批量启动学生的代码空间
  http.patch(import.meta.env.VITE_API_URL + 'codespace/start', async ({ request }) => {
    const body = (await request.json()) as string[]
    const res = Array.from({ length: body.length }).fill(false)
    for (let i = 0; i < body.length; i++) {
      const index = students.findIndex((stu) => stu.id === body[i])
      if (index == -1) {
        res[i] = {
          type: 1,
          uuid: 'uuid',
          info: '学生不存在',
        }
      } else if (students[index].url !== '') {
        res[i] = {
          type: 1,
          uuid: 'uuid',
          info: '学生代码空间已启动',
        }
      } else {
        students[index].url = `http://example.com/${body[i]}`
        res[i] = true
      }
      return HttpResponse.json(res, { status: 201 })
    }
  }),
  // 批量停止学生的代码空间
  http.patch(import.meta.env.VITE_API_URL + 'codespace/stop', async ({ request }) => {
    const body = (await request.json()) as string[]
    const res = Array.from({ length: body.length }).fill(false)
    for (let i = 0; i < body.length; i++) {
      const index = students.findIndex((stu) => stu.id === body[i])
      if (index == -1) {
        res[i] = {
          type: 1,
          uuid: 'uuid',
          info: '学生不存在',
        }
      } else if (students[index].url === '') {
        res[i] = {
          type: 1,
          uuid: 'uuid',
          info: '学生代码空间未启动',
        }
      } else {
        students[index].url = ''
        res[i] = true
      }
      return HttpResponse.json(res, { status: 201 })
    }
  }),
  // 获取学生信息
  http.get(import.meta.env.VITE_API_URL + 'student/*', (info) => {
    const id = info.request.url.split('/').pop() as string
    const index = students.findIndex((stu) => stu.id === id)
    return HttpResponse.json(students[index], { status: 201 })
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
          space_used: 0,
          time_used: 0,
        })
        res[i] = true
      }
    }
    return HttpResponse.json(res, { status: 201 })
  }),
  // 修改学生信息
  http.put(import.meta.env.VITE_API_URL + 'student/:id', async ({ request, params }) => {
    const id = params['id']
    const index = students.findIndex((stu) => stu.id === id)
    if (index === -1) {
      return new HttpResponse('学生不存在', {
        status: 202,
      })
    } else {
      const body = (await request.json()) as StudentInfo
      students[index] = {
        ...students[index],
        ...body,
      }
      return new HttpResponse('成功', {
        status: 201,
      })
    }
  }),
  // 修改学生密码
  http.put(import.meta.env.VITE_API_URL + 'student/:id/pwd', () => {
    return new HttpResponse('成功', {
      status: 201,
    })
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
    return HttpResponse.json(res, { status: 201 })
  }),
  // 获取学生列表
  http.get(import.meta.env.VITE_API_URL + 'student', async ({ request }) => {
    const searchParams = new URLSearchParams(request.url.split('?')[1])
    const page = Number.parseInt(searchParams.get('page') as string)
    const size = Number.parseInt(searchParams.get('size') as string)
    const res = students.slice(page * size, (page + 1) * size)
    return HttpResponse.json(res, {
      status: 201,
      headers: {
        'yatcc-page-here': page.toString(),
        'yatcc-page-size': size.toString(),
        'yatcc-page-total': students.length.toString(),
      },
    })
  }),
  http.put(import.meta.env.VITE_API_URL + 'increase-quota', async ({ request }) => {
    const body = (await request.json()) as IncreaseQuotaParams
    const res = Array.from({ length: body.length }).fill(false)
    for (let i = 0; i < body.length; i++) {
      const { sid, space_quota, time_quota } = body[i]
      const index = students.findIndex((stu) => stu.id === sid)
      if (index !== -1) {
        students[index].space_quota += space_quota
        students[index].time_quota += time_quota
        res[i] = true
      }
    }
    return HttpResponse.json(res, { status: 201 })
  }),
  // 批量添加任务

  // 获取任务详情
]
