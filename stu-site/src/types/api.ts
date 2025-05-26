export type ErrorResponse = {
  type: number // 错误类型，负数为通用错误，正数为专用错误
  uuid: string // 错误唯一标识，用于追踪
  info: string // 人类可读的错误描述信息
}

/**
 * 响应删除请求
 * 当请求删除多个资源时，返回数组，每个元素为布尔值或ErrorResponse
 * 布尔值表示是否成功删除，ErrorResponse表示发生错误
 */
export type ResourceDeletion = (boolean | ErrorResponse)[]

/**
 * 资源创建响应
 * 字符串用于后验资源 ID
 * True 表示先验 ID 创建成功
 * False 表示资源已存在
 * ErrorResponse 用于描述创建失败。
 */
export type ResourceCreation = (string | boolean | ErrorResponse)[]
