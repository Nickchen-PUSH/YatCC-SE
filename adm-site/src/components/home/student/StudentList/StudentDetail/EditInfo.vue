<template>
  <el-dialog
    v-model="isVisible"
    title="修改学生信息"
    style="width: 20rem"
    @close="handleClose"
    append-to-body
  >
    <el-form :model="form" style="padding: 0.5rem">
      <el-form-item label="学生 ID">
        <p>{{ student.id }}</p>
      </el-form-item>
      <el-form-item label="姓名">
        <el-input v-model="form.name" :placeholder="student.name" @keyup.enter="handleEditInfo" />
      </el-form-item>
      <el-form-item label="邮箱">
        <el-input v-model="form.mail" :placeholder="student.mail" @keyup.enter="handleEditInfo" />
      </el-form-item>
      <div class="btn-group">
        <el-button type="primary" @click="handleEditInfo">保存</el-button>
        <el-button @click="isVisible = false">取消</el-button>
      </div>
    </el-form>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { StudentBrief } from '@/types'
import { updateStudent } from '@/api/student'

const isVisible = defineModel<boolean>()

const props = defineProps<{
  student: StudentBrief
}>()

const emit = defineEmits<{
  (e: 'update'): void
}>()

const form = ref({
  mail: '',
  name: '',
})

async function handleEditInfo() {
  if (form.value.mail === '' && form.value.name === '') {
    ElMessage.warning('姓名邮箱均为空，用户信息未修改')
    return
  }
  if (form.value.mail.length > 32 || form.value.name.length > 32) {
    ElMessage.error('姓名或邮箱长度不能超过32个字符')
    return
  }
  form.value.mail = form.value.mail === '' ? props.student.mail : form.value.mail
  form.value.name = form.value.name === '' ? props.student.name : form.value.name
  const res = await updateStudent(props.student.id, form.value)
  if (res === 'Ok') {
    ElMessage.success('修改成功')
  } else {
    ElMessage.error('修改失败')
  }
  emit('update')
  isVisible.value = false
}

function handleClose() {
  form.value = {
    mail: '',
    name: '',
  }
}
</script>

<style scoped></style>
