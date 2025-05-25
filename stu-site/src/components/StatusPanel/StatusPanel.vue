<script setup lang="ts">
import type { CodeSpaceInfo, Status } from '@/types';
import DashBoard from './DashBoard.vue';
import { computed, onMounted, onUnmounted, ref} from 'vue';

import { getCodespaceInfo, startCodespace, stopCodespace } from '@/composables/api/codespace';
const codespaceInfo = ref<CodeSpaceInfo>({
  access_url: '', // 定义 '' 为加载状态，其他同 CodeSpaceInfo
  last_start: new Date(),
  last_stop: new Date(),
  space_quota: 0,
  space_used: 0,
  time_quota: 0,
  time_used: 0,
})

const status = computed<Status>(() => {
  switch (codespaceInfo.value.access_url) {
    case '':
      return '加载中'
    case true:
      return '启动中'
    case false:
      return '已停止'
    default:
      return '运行中'
  }
})
const fetchInfo = async () => {
  const res = await getCodespaceInfo()
  if (res) {
    codespaceInfo.value = res
    return true
  }
  return false
}

// mount后立即刷新，然后每隔一分钟刷新状态
let timer: number | undefined = undefined
onMounted(async () => {
  await fetchInfo()
  timer = setInterval(async () => {
    await fetchInfo()
  }, 60 * 1000)
})

onUnmounted(() => {
  clearInterval(timer)
})
async function handleStart() {
  const result = await startCodespace()
  switch (result) {
    case 'Ok':
      if (status.value !== '加载中') {
        codespaceInfo.value.access_url = true // 表示代码空间正在启动
      }
      ElMessage.success('代码空间正在启动')
      break
    case 'Already Running':
      ElMessage.warning('代码空间已启动')
      break
    case 'Run Out of Quota':
      ElMessage.error('配额不足，无法启动代码空间')
      break
    case 'Error':
      ElMessage.error('启动代码空间失败')
      break
  }
  setTimeout(() => {
    fetchInfo()
  }, 1000)
}
const handleStop = async () => {
  let res = await stopCodespace()
  switch (res) {
    case 'Ok':
      ElMessage.success('代码空间停止成功')
      setTimeout
      break
    case 'Not Running':
      ElMessage.warning('代码空间未启动')
      break
    case 'Error':
      ElMessage.error('停止代码空间失败')
      break
  }

}
async function refresh() {
  const res = await fetchInfo()
  if (res) {
    ElMessage.success('刷新成功')
  } else {
    ElMessage.error('刷新失败')
  }
}
</script>

<template>
  <el-card class="max-w-700px min-w-500px mx-auto shadow-lg dark:bg-#2d2d2d">
    <template #header>
      <div class="flex items-center justify-between">
        <h3 class="text-18px font-bold">代码空间</h3>

      </div>
    </template>
    <div class="flex justify-center items-center gap-8">
      <StatusInfo :status="status" :codespace-info="codespaceInfo" />
      <DashBoard :codespace-info="codespaceInfo" />
    </div>
    <template #footer>
      <div class="flex justify-end space-x-4">
        <el-button
          type="primary"
          @click="handleStart"
        >
          启动
        </el-button>
        <el-button @click="refresh">
          刷新
        </el-button>
        <el-button type="danger" @click="handleStop">
          停止
        </el-button>
      </div>
    </template>
  </el-card>
</template>
