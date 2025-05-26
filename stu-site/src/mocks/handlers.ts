import { http, HttpResponse } from 'msw'

export const handlers = [
  // 登录账户，返回 API key
  http.post(import.meta.env.VITE_API_URL + 'login', () => {
    return new HttpResponse('Token',{status: 201})
  }),
  // 获取用户信息
  http.get(import.meta.env.VITE_API_URL + 'user', () => {
    return HttpResponse.json({
      mail: 'test@test.com',
      name: 'test',
    },{status: 201})
  }),
  // 重置密码
  http.patch(import.meta.env.VITE_API_URL + 'user', () => {
    return new HttpResponse('修改成功',{status: 201})
  }),
  // 修改用户信息
  http.put(import.meta.env.VITE_API_URL + 'user', () => {
    return new HttpResponse('修改成功',{status: 201})
  }),
  // 停止代码空间
  http.delete(import.meta.env.VITE_API_URL + 'codespace', () => {
    return new HttpResponse('停止操作成功',{status: 201})
  }),
  // 进入代码空间
  http.get(import.meta.env.VITE_API_URL + 'codespace', () => {
    return new HttpResponse('容器正在运行，重定向到代码空间页面', {
      status: 302,
      headers: {
        location: 'https://www.baidu.com',
      },
    })
  }),
  // 启动代码空间
  http.post(import.meta.env.VITE_API_URL + 'codespace', () => {
    return new HttpResponse('启动操作成功',{status: 201})
  }),
  // 获取代码空间信息
  http.get(import.meta.env.VITE_API_URL + 'codespace/info', () => {
    return HttpResponse.json({
      access_url: 'https://www.baidu.com',
      last_start: 1637152000,
      last_stop: 1637154400,
      space_quota: 1073741824,
      space_used: 536870912,
      time_quota: 3600,
      time_used: 2400,
    },{status: 201})
  }),
  // 代码空间保活
  http.post(import.meta.env.VITE_API_URL + 'codespace/keepalive', () => {
    return new HttpResponse('成功',{status: 201})
  }),
]
