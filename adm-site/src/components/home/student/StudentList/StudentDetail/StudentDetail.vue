<template>
  <div class="wrapper">
    <el-descriptions v-if="detail">
      <el-descriptions-item label="邮箱">{{ detail.mail }}</el-descriptions-item>
      <el-descriptions-item label="空间使用">
        {{ formatBytes(detail.space_used) }} / {{ formatBytes(detail.space_quota) }}
      </el-descriptions-item>
      <el-descriptions-item label="时间使用">
        {{ formatTime(detail.time_used) }} / {{ formatTime(detail.time_quota) }}
      </el-descriptions-item>
      <el-descriptions-item label="代码空间 url">
        <a href="{{ detail.url }}" target="_blank" v-if="detail.url !== ''">
          {{ detail.url }}
        </a>
        <span v-else>未就绪</span>
      </el-descriptions-item>
      <el-descriptions-item label="同步情况">
        {{ detail.is_synced ? '已同步' : '未同步' }}
      </el-descriptions-item>
      <el-descriptions-item label="作业id">
        {{ detail.job ? detail.job : 'null' }}
      </el-descriptions-item>
      <el-descriptions-item label="操作" span="3">
        <span>
          <el-button small @click="refresh">刷新</el-button>
          <el-button small @click="showEditInfo = true">修改用户信息</el-button>
          <el-button small @click="showEditPwd = true">修改密码</el-button>
          <!-- 如果接口确定，可以条件渲染按钮 -->
          <el-button small @click="handleStartCodeSpace"> 启动代码空间 </el-button>
          <el-button small @click="handleStopCodeSpace"> 停止代码空间 </el-button>
          <el-button small @click="handleSync"> 同步状态 </el-button>
          <el-button small @click="showIncreaseQuota = true"> 增加配额 </el-button>
        </span>
      </el-descriptions-item>
    </el-descriptions>
    <p v-else>Loading...</p>
    <EditInfo :student="student" v-model="showEditInfo" @update="handleEditInfoUpdate" />
    <EditPassword :student="student" v-model="showEditPwd" />
    <IncreaseQuota :id="student.id" v-model="showIncreaseQuota" @update="handleQuotaUpdate" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import type { StudentBrief, StudentDetailInfo } from '@/types'
import { getStudentDetail } from '@/api/student'
import { formatBytes, formatTime } from '@/utils'
import EditInfo from './EditInfo.vue'
import EditPassword from './EditPassword.vue'
import { clearDeadState, startCodespaces, stopCodespaces } from '@/api/codespace'
import IncreaseQuota from './IncreaseQuota.vue'

const props = defineProps<{
  student: StudentBrief
}>()

const emit = defineEmits<{
  (e: 'update'): void
}>()

const detail = ref<StudentDetailInfo | null>(null)
const showEditPwd = ref(false)
const showEditInfo = ref(false)
const showIncreaseQuota = ref(false)

let timer: NodeJS.Timeout | undefined = undefined
onMounted(async () => {
  await refresh()
  timer = setInterval(async () => {
    await refresh()
  }, 60 * 1000)
})
onUnmounted(() => {
  clearInterval(timer)
})

async function refresh() {
  const res = await getStudentDetail(props.student.id)
  if (!res) {
    return false
  }
  detail.value = res
}

async function handleStartCodeSpace() {
  const res = await startCodespaces([props.student.id])
  if (!res) {
    ElMessage.error('网络错误')
    return
  }
  const resData = res[0]
  if (typeof resData === 'boolean' && resData) {
    ElMessage.success('启动成功')
  } else if (typeof resData === 'boolean' && !resData) {
    ElMessage.error('启动失败')
  } else {
    ElMessage.error('未知错误')
    console.error(resData)
  }
}

async function handleStopCodeSpace() {
  const res = await stopCodespaces([props.student.id])
  if (!res) {
    ElMessage.error('网络错误')
    return
  }
  const resData = res[0]
  if (typeof resData === 'boolean' && resData) {
    ElMessage.success('停止成功')
  } else if (typeof resData === 'boolean' && !resData) {
    ElMessage.error('停止失败')
  } else {
    ElMessage.error('未知错误')
    console.error(resData)
  }
}

async function handleSync() {
  const response = await clearDeadState([props.student.id])
  if (!response) {
    ElMessage.error('网络错误')
    return
  }
  const res = response[0]
  if (typeof res === 'boolean' && res) {
    ElMessage.success('同步成功')
  } else if (typeof res === 'boolean' && !res) {
    ElMessage.error('同步失败')
  } else {
    ElMessage.error('未知错误')
    console.error(res)
  }
  refresh()
}

function handleQuotaUpdate(space_quota: number, time_quota: number) {
  if (!detail.value) {
    return
  }
  detail.value.space_quota += space_quota
  detail.value.time_quota += time_quota
}

function handleEditInfoUpdate() {
  refresh()
  emit('update')
}
</script>

<style scoped>
.wrapper {
  padding: 0.5rem 1rem 0.5rem 2rem;
}
</style>
