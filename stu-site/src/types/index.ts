export type UserInfo = {
  mail: string
  name: string
}

// 前端 api 层会将时间戳转换为日期格式，将字节转换为可读格式
export type CodeSpaceInfo = {
  access_url: string | boolean // 访问链接，true 表示代码空间正在启动，false 表示代码空间已停止
  last_start: Date // 上次启动时间
  last_stop: Date // 上次停止时间
  space_quota: number // 空间配额，单位为字节
  space_used: number // 空间已用，单位为字节
  time_quota: number // 时间配额，单位为秒
  time_used: number // 时间已用，单位为秒
}

export type Status = '加载中' | '启动中' | '运行中' | '已停止'
