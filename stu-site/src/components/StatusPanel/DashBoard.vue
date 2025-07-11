<script setup lang="ts">
import { computed } from 'vue'
import type { CodeSpaceInfo } from '@/types'
import { formatTime } from '@/composables/utils/format'

const props = defineProps<{
  codespaceInfo: CodeSpaceInfo
}>()


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

    <el-progress type="dashboard" :percentage="time_percentage"
    class="flex justify-center items-center" :color="colors" width=240 stroke-width="20">
      <template #default>
        <div class="text-4xl">剩余时间</div>
        <div class="text-xl">
          {{ formatTime(codespaceInfo.time_quota - codespaceInfo.time_used) }}
        </div>

      </template>
    </el-progress>
  </div>
</template>

