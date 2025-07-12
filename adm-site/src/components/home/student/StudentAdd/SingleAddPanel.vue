<template>
  <el-card header="添加单个学生">
    <el-form :model="form" label-width="5rem" ref="formRef" :rules="rules">
      <el-form-item label="学号" prop="id">
        <el-input v-model="form.id" class="input-field"></el-input>
      </el-form-item>
      <el-form-item label="邮箱" prop="mail">
        <el-input v-model="form.mail" class="input-field"></el-input>
      </el-form-item>
      <el-form-item label="姓名" prop="name">
        <el-input v-model="form.name" class="input-field"></el-input>
      </el-form-item>
      <el-form-item label="密码" prop="pwd">
        <el-input v-model="form.pwd" class="input-field" type="password"></el-input>
      </el-form-item>
      <el-form-item label="时间配额" prop="time_quota">
        <TimeInput v-model="form.time_quota"></TimeInput>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="handleSubmit(formRef)">提交</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { addStudents } from '@/api/student'
import SpaceInput from '@/components/common/SpaceInput.vue'
import TimeInput from '@/components/common/TimeInput.vue'
import type { FormInstance } from 'element-plus'

const form = ref({
  id: '',
  mail: '',
  name: '',
  pwd: '',
  space_quota: 0,
  time_quota: 0,
})
const formRef = ref<FormInstance>()

const rules = {
  id: [
    { required: true, message: '请输入学号', trigger: 'blur' },
    { pattern: /^[0-9]{8}$/, message: '学号为8位数字', trigger: 'blur' },
  ],
  mail: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式错误', trigger: 'blur' },
  ],
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { max: 128, message: '姓名长度不能超过128个字符', trigger: 'blur' },
  ],
  pwd: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 128, message: '密码长度必须在6到128个字符之间', trigger: 'blur' },
  ],
  space_quota: [{ required: true, message: '请输入空间配额', trigger: 'blur' }],
  time_quota: [{ required: true, message: '请输入时间配额', trigger: 'blur' }],
}

async function handleSubmit(formEl: FormInstance | undefined) {
  if (!formEl) return
  await formEl.validate(async (isValid) => {
    if (isValid) {
      const result = await addStudents([
        {
          id: form.value.id,
          mail: form.value.mail,
          name: form.value.name,
          pwd: form.value.pwd,
          time_quota: form.value.time_quota,
        },
      ])
      if (result) {
        ElMessage.success('添加成功')
      } else {
        ElMessage.error('添加失败')
      }
    } else {
      ElMessage.error('请检查输入')
    }
  })
}
</script>

<style scoped></style>
