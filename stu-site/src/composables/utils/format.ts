// 对字节进行格式化，decimals 表示小数点后四舍五入保留几位。输入取整
function formatBytes(bytes: number, decimals = 2) {
  bytes = Math.floor(bytes)
  if (bytes === 0) return '0 B'

  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']

  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

// 对秒数进行格式化。输入取整
function formatTime(seconds: number) {
  seconds = Math.floor(seconds)
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${hours}小时${minutes}分钟`
}

export { formatBytes, formatTime }
