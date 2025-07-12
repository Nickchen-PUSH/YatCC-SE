export type StudentBrief = {
  id: string
  name: string
  mail: string
}
export type StudentInfo = {
  name: string
  mail: string
}

export type Task = {
  args: string[]
  cmd: string
  cwd: string | null
  desc: string
  detach: boolean
  env: object | null
  loop_count: number
  loop_cycle: number | null
  resumable: boolean
  stderr: string | null
  stdin: string | null
  stdout: string | null
}

// CodespaceJob = RootModel[tuple[str, str] | None]
export type CodespaceJob = [string, string] | null

// 前端 api 层会将时间戳转换为日期格式，将字节转换为可读格式
export type CodespaceInfo = {
  is_synced: boolean // 与星光平台的状态是否一致同步
  job: CodespaceJob // 作业 ID（如果已启动）
  url: string // 访问链接（未就绪时为空串）
  last_start: number // 上次启动时间
  last_stop: number // 上次停止时间
  space_quota: number // 空间配额，单位为字节
  space_used: number // 空间已用，单位为字节
  time_quota: number // 时间配额，单位为秒
  time_used: number // 时间已用，单位为秒
}

export type StudentDetailInfo = {
  id: string // 学生 ID
  is_synced: boolean // 与星光平台的状态是否一致同步
  job: string | null // 作业 ID（如果已启动）
  mail: string // 学生邮箱
  name: string // 学生姓名
  space_quota: number // 空间配额，单位为字节
  space_used: number // 空间已用，单位为字节
  time_quota: number // 时间配额，单位为秒
  time_used: number // 时间已用，单位为秒
  url: string // 访问链接（未就绪时为空串）
}

// 当响应要求用户重新登录时，抛出此错误
export class UnauthorizedError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'UnauthorizedError'
  }
}
