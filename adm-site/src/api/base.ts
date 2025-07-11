import { getAPIKEY, handleUnauthorized} from '@/api/auth.ts'
import { h } from 'vue'
type Method = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
type RequestOptions = {
  route: string
  method: Method
  auth?: boolean
  data?: Record<string, unknown> | unknown[] | string
}

// fetch API 请求封装
async function request({
  route,
  method,
  auth = true,
  data = undefined,
}: RequestOptions): Promise<Response | null> {
  const headers = new Headers()
  headers.append('Content-Type', 'application/json')

  if (auth && !getAPIKEY()) {
    handleUnauthorized()
    return null
  } else {
    headers.append('ADM-API-KEY', getAPIKEY() || '')
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

    // 检查APIKEY状态
    if (response.status === 403) {
      ElMessageBox.alert('APIKEY无效', {
        confirmButtonText: '确定',
        type: 'error',
      })
      return null
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


export default request
