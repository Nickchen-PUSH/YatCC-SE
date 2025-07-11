<template>
  <el-dialog v-model="isVisible" title="增加学生配额" @close="handleClose" append-to-body>
    <p>ID: {{ id }}</p>
    <el-form :model="form" style="padding: 0.5rem">
      <el-form-item label="增加空间配额">
        <SpaceInput v-model="form.increaseSpace" />
      </el-form-item>
      <el-form-item label="增加时间配置">
        <TimeInput v-model="form.increaseTime" />
      </el-form-item>
      <div class="btn-group">
        <el-button type="primary" @click="submit">提交</el-button>
        <el-button @click="isVisible = false">取消</el-button>
      </div>
    </el-form>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import SpaceInput from '../../../../common/SpaceInput.vue'
import TimeInput from '../../../../common/TimeInput.vue'
import { increaseQuota } from '@/api/student'

const isVisible = defineModel<boolean>()

const props = defineProps<{
  id: string
}>()

const emit = defineEmits<{
  (e: 'update', space_quota: number, time_quota: number): void
}>()

const form = ref({
  increaseSpace: 0,
  increaseTime: 0,
})

async function submit() {
  const res = await increaseQuota([
    {
      sid: props.id,
      space_quota: form.value.increaseSpace,
      time_quota: form.value.increaseTime,
    },
  ])
  if (!res) {
    ElMessage.error('网络错误')
  } else if (res[0] === true) {
    ElMessage.success('增加配额成功')
    emit('update', form.value.increaseSpace, form.value.increaseTime)
  } else {
    ElMessage.error('增加配额失败')
    console.error(res[0])
  }
  handleClose()
}

function handleClose() {
  form.value = {
    increaseSpace: 0,
    increaseTime: 0,
  }
  isVisible.value = false
}
</script>

<style scoped>
.btn-group {
  display: flex;
  justify-content: flex-end;
}
</style>
