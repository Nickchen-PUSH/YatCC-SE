import { type StudentDetailInfo } from '@/types'

export const students: StudentDetailInfo[] = [
  {
    id: '00000001',
    is_synced: true,
    job: 'job123',
    mail: 'student1@example.com',
    name: 'Alice',
    space_quota: 1024 * 1024 * 1024, // 1GB
    space_used: 512 * 1024 * 1024, // 512MB
    time_quota: 3600, // 1小时
    time_used: 1800, // 30分钟
    url: 'https://example.com/student1',
  },
  {
    id: '00000002',
    is_synced: false,
    job: null,
    mail: 'student2@example.com',
    name: 'Bob',
    space_quota: 512 * 1024 * 1024, // 512MB
    space_used: 256 * 1024 * 1024, // 256MB
    time_quota: 1800, // 30分钟
    time_used: 900, // 15分钟
    url: '',
  },
  {
    id: '00000003',
    is_synced: true,
    job: 'job456',
    mail: 'student3@example.com',
    name: 'Charlie',
    space_quota: 2 * 1024 * 1024 * 1024, // 2GB
    space_used: 1 * 1024 * 1024 * 1024, // 1GB
    time_quota: 7200, // 2小时
    time_used: 3600, // 1小时
    url: 'https://example.com/student3',
  },
  {
    id: '00000004',
    is_synced: true,
    job: null,
    mail: 'student4@example.com',
    name: 'David',
    space_quota: 1024 * 1024 * 1024, // 1GB
    space_used: 256 * 1024 * 1024, // 256MB
    time_quota: 3600, // 1小时
    time_used: 1200, // 20分钟
    url: 'https://example.com/student4',
  },
  {
    id: '00000005',
    is_synced: false,
    job: 'job789',
    mail: 'student5@example.com',
    name: 'Eve',
    space_quota: 512 * 1024 * 1024, // 512MB
    space_used: 128 * 1024 * 1024, // 128MB
    time_quota: 1800, // 30分钟
    time_used: 600, // 10分钟
    url: '',
  },
]
