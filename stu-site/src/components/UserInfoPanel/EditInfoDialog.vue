<script setup lang="ts">
import { ref } from 'vue'
import type {FormInstance } from 'element-plus'


export interface UserInfo {
  name: string
  mail: string
}

const visible = ref(false)
const formRef = ref<FormInstance>()
const formData = ref<UserInfo>({ name: '', mail: '' })

const rules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  mail: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ]
}

// 暴露给父组件的方法
const openDialog = (userInfo: UserInfo) => {
  formData.value = { ...userInfo }
  visible.value = true
}

const closeDialog = () => {
  visible.value = false
}
// 提交表单
const emit = defineEmits<{
  (e: 'updateInfo', data: UserInfo): void
}>()
const submitForm = async () => {
  try {
    await formRef.value?.validate()
    await emit('updateInfo', formData.value)

  } catch (e) {
    console.log('表单验证失败')
  }
}

defineExpose({ openDialog, closeDialog })
</script>

<template>
  <el-dialog
    v-model="visible"
    title="编辑个人信息"
    width="500px"
    class="rounded-8px dark:bg-#2d2d2d"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="80px"
    >
      <el-form-item label="姓名" prop="name">
        <el-input v-model="formData.name" />
      </el-form-item>
      <el-form-item label="邮箱" prop="email">
        <el-input v-model="formData.mail" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="submitForm">确认修改</el-button>
    </template>
  </el-dialog>
</template>
