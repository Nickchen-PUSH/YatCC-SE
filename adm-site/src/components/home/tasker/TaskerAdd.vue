<template>
  <el-card>
    <template #header>
      <span>新增任务</span>
    </template>
    <el-form :model="form" ref="taskerForm" label-width="5rem">
      <el-form-item label="命令">
        <el-input v-model="form.cmd" />
      </el-form-item>
      <el-form-item label="参数">
        <el-input v-model="argsInput" @input="updateArgs" placeholder="多个参数请用空格分隔" />
      </el-form-item>
      <el-form-item label="工作目录">
        <el-input v-model="form.cwd" />
      </el-form-item>
      <el-form-item label="环境变量">
        <el-input v-model="form.env" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.desc" />
      </el-form-item>
      <el-form-item label="循环执行">
        <el-switch v-model="form.is_looped" />
      </el-form-item>
      <el-form-item label="可恢复">
        <el-switch v-model="form.is_resumable" />
      </el-form-item>
      <el-form-item label="执行时间">
        <el-date-picker
          v-model="whenInput"
          @change="updateWhen"
          type="datetime"
          placeholder="执行时间"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onSubmit">提交</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const initialForm = () => ({
  args: [],
  cmd: '',
  cwd: null,
  desc: '',
  env: null,
  id: 0, // API 文档修改中，目前仅作占位
  is_looped: false,
  is_resumable: false,
  when: 0, // Unix 时间戳，单位秒
})

const form = ref(initialForm())
const argsInput = ref<string>('')
const whenInput = ref<Date>(new Date())

const emit = defineEmits<{
  submitOk: []
}>()

const updateArgs = () => {}

const updateWhen = () => {
  // 单位是 ms
  form.value.when = Math.floor(whenInput.value.getTime())
}

const onSubmit = () => {
  // TODO: 提交表单
  console.log(form.value)
  // TODO: 如果成功，返回 id, 组合后返回给父组件
  emit('submitOk')
  form.value = initialForm()
}
</script>

<style scoped></style>
