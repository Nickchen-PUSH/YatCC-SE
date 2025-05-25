<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import { resetPassword } from '@/composables/api/userinfo'

interface PasswordForm {
  oldPassword: string
  newPassword: string
  confirmPassword: string
}

const visible = ref(false)
const formRef = ref<FormInstance>()
const formData = ref<PasswordForm>({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const rules = {
  oldPassword: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 18, message: '长度在 6 到 18 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { validator: (_: unknown, value: string, callback: (error?: Error) => void) => {
      if (value !== formData.value.newPassword) {
        callback(new Error('两次输入密码不一致'))
      } else {
        callback()
      }
    }, trigger: 'blur' }
  ]
}

// 暴露给父组件的方法
const openDialog = () => {
  visible.value = true
}

// 提交表单

const submitForm = async () => {
  try {
    await formRef.value?.validate()
    const res = await resetPassword(formData.value.oldPassword, formData.value.newPassword)
    if (res === 'Ok') {
      ElMessage.success('密码修改成功')
      visible.value = false
    }
    else{
      ElMessage.error('密码修改失败')
      formData.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
    }

  } catch (e) {
    console.log('表单验证失败')
  }
}

defineExpose({ openDialog })
</script>

<template>
  <el-dialog
    v-model="visible"
    title="修改密码"
    width="500px"
    class="rounded-8px dark:bg-#2d2d2d"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="100px"
    >
      <el-form-item label="旧密码" prop="oldPassword">
        <el-input
          v-model="formData.oldPassword"
          type="password"
          show-password
        />
      </el-form-item>
      <el-form-item label="新密码" prop="newPassword">
        <el-input
          v-model="formData.newPassword"
          type="password"
          show-password
        />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirmPassword">
        <el-input
          v-model="formData.confirmPassword"
          type="password"
          show-password
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="submitForm">确认修改</el-button>
    </template>
  </el-dialog>
</template>
