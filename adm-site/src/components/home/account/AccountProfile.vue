<script setup lang="ts">

import { clearAPIKEY, setAPIKEY } from '@/api/auth'
import { type FormInstance } from 'element-plus'
import { ref } from 'vue'


const formRef = ref()
const form = ref({
  apiKey: '',
  checkApiKey: '',
})





const rules = {
  apiKey: [
    { required: true, message: '请输入 API-KEY', trigger: 'blur' },
    { min: 6, max: 128, message: 'API-KEY 长度必须在6到128个字符之间', trigger: 'blur' },
  ],
}

async function updateApiKey(formEl: FormInstance | undefined) {
  setAPIKEY(form.value.apiKey)
  ElMessage.success('API-KEY 设置成功')
}


</script>


<template>
  <ElCard>
    <template #header>
      <h2>修改 API-KEY</h2>
    </template>
    <el-form ref="formRef" :model="form" :rules="rules">
      <el-form-item label="设置 API-KEY" prop="apiKey">
        <el-input v-model="form.apiKey" type="password"></el-input>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="updateApiKey(formRef)">设置</el-button>
        <el-button type="danger" @click="clearAPIKEY()">重置</el-button>
      </el-form-item>
    </el-form>
  </ElCard>
</template>



