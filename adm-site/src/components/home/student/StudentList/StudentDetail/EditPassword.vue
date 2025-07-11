<template>
  <el-dialog
    v-model="isVisible"
    title="修改密码"
    style="width: 20rem"
    @close="handleClose"
    append-to-body
  >
    <el-form :model="form" label-width="5rem" style="padding: 0.5rem">
      <el-form-item label="新密码">
        <el-input type="password" v-model="form.newPassword" @keyup.enter="handleEditPassword" />
      </el-form-item>
      <div class="btn-group">
        <el-button type="primary" @click="handleEditPassword">保存</el-button>
        <el-button @click="isVisible = false">取消</el-button>
      </div>
    </el-form>
  </el-dialog>
</template>

<script setup lang="ts">
import { resetStudentPassword } from '@/api/student'
import type { StudentBrief } from '@/types'
import { ref } from 'vue'

const isVisible = defineModel<boolean>()

const props = defineProps<{
  student: StudentBrief
}>()

const form = ref({
  newPassword: '',
})

async function handleEditPassword() {
  if (form.value.newPassword.length < 8) {
    ElMessage.error('密码长度不能少于8个字符')
  } else if (form.value.newPassword.length > 128) {
    ElMessage.error('密码长度不能超过128个字符')
  } else {
    const res = await resetStudentPassword(props.student.id, form.value.newPassword)
    if (res === 'Ok') {
      ElMessage.success('修改成功')
      isVisible.value = false
    } else {
      ElMessage.error('修改失败')
    }
  }
  form.value.newPassword = ''
}

function handleClose() {
  form.value = {
    newPassword: '',
  }
}
</script>

<style scoped></style>
