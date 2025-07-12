import { describe, it, expect } from 'vitest'
import { formatBytes } from '../index'

describe('formatBytes', () => {
  it('整数单位转换', () => {
    expect(formatBytes(0)).toBe('0 B')
    expect(formatBytes(1024)).toBe('1 KiB')
    expect(formatBytes(1024 * 1024)).toBe('1 MiB')
    expect(formatBytes(1024 * 1024 * 1024)).toBe('1 GiB')
  })
  it('小数单位转换', () => {
    expect(formatBytes(1024 * 1024 * 1.1234)).toBe('1.12 MiB')
    expect(formatBytes(1024 * 1024 * 1.1234, 1)).toBe('1.1 MiB')
    expect(formatBytes(1024 * 1024 * 1.1234, 2)).toBe('1.12 MiB')
    expect(formatBytes(1024 * 1024 * 1.1234, 3)).toBe('1.123 MiB')
  })
})
