// 对字节进行格式化，decimals 表示小数点后四舍五入保留几位
function formatBytes(bytes: number, decimals = 2) {
  const unit = ['B', 'KB', 'MB', 'GB']
  let num = bytes
  let i = 0
  while (num >= 1024 && i < unit.length - 1) {
    num /= 1024.0
    i++
  }

  return num.toFixed(decimals) + ' ' + unit[i]
}

// 对秒数进行格式化
function formatTime(seconds: number, decimals = 2) {
  const unit = ['秒', '分钟', '小时']

  let num = seconds
  let i = 0
  while (num >= 60 && i < unit.length - 1) {
    num /= 60.0
    i++
  }

  return num.toFixed(decimals) + ' ' + unit[i]
}

export { formatBytes, formatTime }
