<script setup lang="ts">
import type { CodeSpaceInfo, Status } from '@/types';
import ClipBoard from '../ui/ClipBoard.vue';
import { getToken } from '@/composables/auth';
import { computed ,ref} from 'vue';

const props = defineProps<{
  status: Status
  codespaceInfo: CodeSpaceInfo
}>()
const statusType = computed<string>(() => {
  switch (props.status) {
    case '加载中':
      return 'info'
    case '启动中':
      return 'primary'
    case '已停止':
      return 'danger'
    default:
      return 'success'
  }
})

const pwdVisible = ref(false)

</script>

<template>
  <div class="flex flex-col gap-6 h-full flex-1">

    <div>
      <label class="text-gray-500 dark:text-gray-400">当前状态：</label>
      <el-tag :type="statusType">{{ status }}</el-tag>
    </div>
  <!-- 链接部分 -->
  <div class="flex items-center">
    <label class="text-gray-500 dark:text-gray-400 flex items-center ">
      <div class="i-mdi:link mr-1 text-20px" />
      链接：
    </label>
    <el-link type="primary" :href="typeof codespaceInfo.access_url === 'boolean' ? '' : codespaceInfo.access_url" target="_blank" class="text-16px">
      {{ typeof codespaceInfo.access_url === 'boolean' ? '' : codespaceInfo.access_url }}
    </el-link>
  </div>
  <!-- 密码部分 -->
  <div class="flex items-center">
    <label class="text-gray-500 dark:text-gray-400 flex items-center">
      <div class="i-mdi:key mr-1 text-20px" />
      密码：
    </label>
    <div class="flex items-center">
      <el-tooltip :content="pwdVisible ? '双击隐藏' : '双击显示'"
      placement="bottom" hide-after="100">
        <span class="text-16px pr-2 cursor-pointer" @dblclick="pwdVisible = !pwdVisible">
          {{pwdVisible ? getToken() : '*********'}}
        </span>
      </el-tooltip>
      <ClipBoard :text="getToken() as string" @callback="() => pwdVisible = !pwdVisible"/>
    </div>
  </div>

</div>
</template>

<style scoped>
.el-link {
  font-size: 16px;
}
.el-tag {
  font-size: 14px;
}
</style>
