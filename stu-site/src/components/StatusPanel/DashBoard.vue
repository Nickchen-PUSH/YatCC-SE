<script setup lang="ts">
import { computed } from 'vue'
import type { CodeSpaceInfo } from '@/types'
import { formatBytes, formatTime } from '@/composables/utils/format'

const props = defineProps<{
  codespaceInfo: CodeSpaceInfo
}>()

const space_percentage = computed(() => {
  return props.codespaceInfo.space_quota === 0
    ? 100
    : (props.codespaceInfo.space_used / props.codespaceInfo.space_quota) * 100
})
const time_percentage = computed(() => {
  return props.codespaceInfo.time_quota === 0
    ? 0
    : (1 - props.codespaceInfo.time_used / props.codespaceInfo.time_quota) * 100
})

const colors = [
  { color: '#f56c6c', percentage: 20 },
  { color: '#e6a23c', percentage: 40 },
  { color: '#5cb87a', percentage: 60 },


]
</script>


<template>
  <div class="flex justify-center items-center gap-4 flex-col">
    <el-progress type="dashboard" :percentage="space_percentage"
    class="flex justify-center items-center" :color="colors">
      <template #default>
        <div class="text-xl">存储空间</div>
        <div class="text-12px">
          {{ formatBytes(codespaceInfo.space_used) }} /
          {{ formatBytes(codespaceInfo.space_quota) }}
        </div>

      </template>
    </el-progress>
    <el-progress type="dashboard" :percentage="time_percentage"
    class="flex justify-center items-center" :color="colors">
      <template #default>
        <div class="text-xl">剩余时间</div>
        <div class="text-12px">
          {{ formatTime(codespaceInfo.time_quota - codespaceInfo.time_used) }}
        </div>

      </template>
    </el-progress>
  </div>
</template>

