<template>
  <el-card style="max-width: 480px">
    <template #header>
      <div class="card-header">
        <h1>管理员登录</h1>
      </div>
    </template>
    <el-form :model="form" label-width="auto">
      <el-form-item label="管理员API-key">
        <el-input data-test="input-pwd" v-model="form.apikey" type="password" />
      </el-form-item>
      <div>
        <el-button data-test="btn-submit" type="primary" @click="handleLogin">登录</el-button>
      </div>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { authAdmin } from '@/api/admin'

const router = useRouter()

const form = reactive({
  apikey: '',
})

async function handleLogin() {
  if (form.apikey == '') {
    ElMessage.error('请输入管理员API-key')
    return
  }

  const res = await authAdmin(form.apikey)
  switch (res) {
    case 'Ok':
      ElMessage.success('登录成功')
      router.push('/student-list')
      break
    case 'Failed':
      ElMessage.error('管理员API-key错误')
      break
    case 'Error':
      ElMessage.error('网络错误')
      break
  }
}
</script>

<style scoped></style>
