<script setup lang="ts">
import { login } from '@/composables/api/login'
import router from '@/routes'
import type { FormInstance } from 'element-plus'
import { reactive, ref } from 'vue'


// 表单数据
const form = reactive({
  username: '',
  password: ''
})
const formRef = ref<FormInstance>()
// 表单验证规则
const rules = {
  username: [
    { required: true, message: '用户名不能为空', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '密码不能为空', trigger: 'blur' },
  ]
}

// 登录处理
const handleLogin = async () => {
  try{
    await formRef.value?.validate()
    const res = await login(form.username, form.password)
    if (res === 'Ok') {
      router.push('/')
    }
    else if (res === 'Failed') {
      ElMessage.error('学号或密码错误')
    }
    else{
      ElMessage.error('登录失败')
    }
  }catch(e){
    console.log('表单验证失败')
  }

}

</script>

<template>
  <div class="py-48 flex">
    <!-- 登录卡片容器 -->
    <div class="m-auto bg-white dark:bg-#2c2c2c rounded-2xl shadow-lg p-8 w-90vw max-w-400px
             transition-all duration-300 hover:shadow-xl dark:shadow-gray-800/30">
      <!-- 标题部分 -->
      <div class="text-center mb-6">
        <h1 class="text-4xl font-bold text-#409EFF mb-2 select-none">YatCC-SE</h1>
      </div>

      <!-- 表单部分 -->
      <el-form :model="form" :rules="rules" ref="formRef">
        <!-- 用户名输入 -->
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            class="w-full h-12 "
          >
            <template #prefix>
              <div class="i-mdi:account"/>
            </template>
          </el-input>
        </el-form-item>

        <!-- 密码输入 -->
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
            class="w-full h-12"
          >
            <template #prefix>
              <div class="i-mdi:lock" />
            </template>
          </el-input>
        </el-form-item>

        <!-- 登录按钮 -->
        <el-button
          type="primary"
          size="large"
          class="w-full text-8"
          @click="handleLogin"
        >
              立即登录
        </el-button>
      </el-form>

    </div>
  </div>
</template>

