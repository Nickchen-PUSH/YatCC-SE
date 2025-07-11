<template>
  <ElCard>
    <template #header>
      <h2>修改 API-KEY</h2>
    </template>
    <el-form ref="formRef" :model="form" :rules="rules">
      <el-form-item label="更新 API-KEY" prop="apiKey">
        <el-input v-model="form.apiKey" type="password"></el-input>
      </el-form-item>
      <el-form-item label="确认 API-KEY" prop="checkApiKey">
        <el-input v-model="form.checkApiKey" type="password"></el-input>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="updateApiKey(formRef)">更新</el-button>
        <el-button type="danger" @click="handelLogout">退出</el-button>
      </el-form-item>
    </el-form>
  </ElCard>
</template>

<script setup lang="ts">
import { setAdminAPIkey } from '@/api/admin'
import { clearAPIKEY } from '@/api/auth'
import { type FormInstance } from 'element-plus'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const formRef = ref()
const form = ref({
  apiKey: '',
  checkApiKey: '',
})

const router = useRouter()

const validateApiKey = (rule: unknown, value: string, callback: (error?: Error) => void) => {
  if (value !== form.value.apiKey) {
    callback(new Error('两次输入的 API-KEY 不一致'))
  } else {
    callback()
  }
}

const rules = {
  apiKey: [
    { required: true, message: '请输入 API-KEY', trigger: 'blur' },
    { min: 6, max: 128, message: 'API-KEY 长度必须在6到128个字符之间', trigger: 'blur' },
  ],
  checkApiKey: [
    { required: true, message: '请再次输入 API-KEY', trigger: 'blur' },
    { validator: validateApiKey, trigger: 'blur' },
  ],
}

async function updateApiKey(formEl: FormInstance | undefined) {
  if (!formEl) return
  await formEl.validate(async (isValid) => {
    if (!isValid) return
    const apiKey = form.value.apiKey
    const result = await setAdminAPIkey(apiKey)
    if (result === 'Ok') {
      ElMessage.success('API-KEY 更新成功')
      handelLogout()
    } else if (result === 'Failed') {
      ElMessage.error('API-KEY 更新失败')
    } else {
      ElMessage.error('API-KEY 更新失败，请检查网络连接')
    }
  })
}

const handelLogout = () => {
  clearAPIKEY()
  router.push('/auth')
}
</script>

<style scoped></style>
