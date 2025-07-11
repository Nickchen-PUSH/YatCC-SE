import type { ErrorResponse } from '@/types/api'
import { getAPIKEY, handleUnauthorized } from './auth'
import { h } from 'vue'
type Method = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
type RequestOptions = {
  route: string
  method: Method
  igoreAuthFailed?: boolean // 忽略授权失败错误，不进行任何处理
  data?: Record<string, unknown> | unknown[] | string
}

// fetch API 请求封装
// 授权请求时默认拦截 401 和 403，并返回 null
// 30x 默认被浏览器自动处理，可选择拦截
async function request({
  route,
  method,
  igoreAuthFailed = false,
  data = undefined,
}: RequestOptions): Promise<Response | null> {
  const headers = new Headers()
  headers.append('Content-Type', 'application/json')

  // 所有 API 都需要 APIKEY
  if (!getAPIKEY()) {
    handleUnauthorized()
    return null
  } else {
    headers.append('yatcc-api-key', getAPIKEY() || '')
  }

  // 设置请求体
  data = JSON.stringify(data)
  const body = data

  try {
    // 发起请求
    const response = await fetch(import.meta.env.VITE_API_URL + route, {
      method,
      headers,
      body,
    })

    // 统一错误代码
    if (response.status == 202) {
      return handleError(response, igoreAuthFailed)
    }

    // 服务器错误
    if (response.status >= 500) {
      console.error('服务器内部错误', response)
      const message = h('p', [
        h('p', `请求地址：${response.url}`),
        h('p', `状态码：${response.status}`),
        h('p', `响应体：${await response.text()}`),
      ])
      ElMessageBox.alert(message, `很抱歉，服务器发生了错误`, {
        confirmButtonText: '确定',
        type: 'error',
      })
      return null
    }

    // 其他状态码不应出现
    if (response.status != 201) {
      console.error('未知响应状态码', response)
      ElMessageBox.alert('请在控制台查看完整响应', `未知响应状态码 ${response.status}`, {
        confirmButtonText: '确定',
        type: 'error',
      })
      return null
    }

    return response
  } catch (error) {
    console.error('服务器连接失败', error)
    ElMessageBox.alert(`Error: ${error}`, '服务器连接失败，请联系助教解决', {
      confirmButtonText: '确定',
      type: 'error',
    })
    return null
  }
}

async function handleError(response: Response, igoreAuthFailed: boolean): Promise<Response | null> {
  const data: ErrorResponse = await response.json()
  if (data.type === -2 && igoreAuthFailed) {
    return response
  }
  let title
  switch (data.type) {
    case -1:
      title = '一般错误'
      break
    case -2:
      title = 'API-KEY 未通过检查'
      handleUnauthorized()
      break
    case -3:
      title = '锁错误，系统正忙请稍后重试'
      break
    case -4:
      title = '进入死状态，拒绝所有后续修改'
      break
  }
  let message = h('p', [
    h('p', `请求地址：${response.url}`),
    h('p', `uuid：${data.uuid}`),
    h('p', `错误信息： ${data.info}`),
  ])
  ElMessageBox.alert(message, title, {
    confirmButtonText: '确定',
    type: 'error',
  })
  return null
}

export default request
