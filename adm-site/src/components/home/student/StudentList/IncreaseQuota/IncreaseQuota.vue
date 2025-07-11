<template>
  <el-dialog v-model="isVisible" title="批量增加学生配额" @close="handleClose" append-to-body>
    <el-form :model="form" style="padding: 0.5rem">
      <el-form-item label="范围">
        <el-switch v-model="form.global" active-text="全局" inactive-text="选中" />
      </el-form-item>
      <el-form-item label="条件" class="condition">
        <span>空间</span>
        <el-switch v-model="form.enableSpaceCondition" />
        <span>时间</span>
        <el-switch v-model="form.enableTimeCondition" />
      </el-form-item>
      <el-form-item label="剩余空间小于" v-if="form.enableSpaceCondition">
        <SpaceInput v-model="form.spaceLessThan" />
      </el-form-item>
      <el-form-item label="剩余时间小于" v-if="form.enableTimeCondition">
        <TimeInput v-model="form.timeLessThan" />
      </el-form-item>
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
import { h, ref } from 'vue'
import SpaceInput from '@/components/common/SpaceInput.vue'
import TimeInput from '@/components/common/TimeInput.vue'

const isVisible = defineModel<boolean>()

const props = defineProps<{
  selected: string[]
}>()

const formInit = {
  global: true,
  enableSpaceCondition: false,
  enableTimeCondition: false,
  spaceLessThan: 0,
  timeLessThan: 0,
  increaseSpace: 0,
  increaseTime: 0,
}
const form = ref(formInit)

async function submit() {
  ElMessageBox.confirm(
    h('p', [
      h('p', `全局：${form.value.global ? '全局' : '选中'}`),
      h(
        'p',
        `时间条件：${form.value.enableTimeCondition ? `${form.value.timeLessThan} 秒` : '不限制'}`,
      ),
      h(
        'p',
        `空间条件：${form.value.enableSpaceCondition ? `${form.value.spaceLessThan} B` : '不限制'}`,
      ),
      h('p', `增加空间配额：${form.value.increaseSpace} B`),
      h('p', `增加时间配置：${form.value.increaseTime} 秒`),
    ]),
    '功能占位符',
  )
}

function handleClose() {
  form.value = formInit
  isVisible.value = false
}
</script>

<style scoped>
.condition span,
.el-switch {
  margin-right: 0.5rem;
}

.btn-group {
  display: flex;
  justify-content: flex-end;
}
</style>
