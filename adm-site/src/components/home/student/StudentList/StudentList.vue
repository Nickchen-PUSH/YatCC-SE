<template>
  <div>
    <span class="btn-group">
      <h1 class="title">学生列表</h1>
      <el-button @click="refresh">刷新</el-button>
      <el-button type="danger" @click="handleDeleteSelected">删除</el-button>
    </span>
  </div>
  <el-table :data="tableData" row-key="id" stripe @selection-change="handleSelectionChange">
    <el-table-column type="expand">
      <template #default="props">
        <StudentDetail :student="props.row" @update="refresh" />
      </template>
    </el-table-column>
    <el-table-column prop="name" label="姓名"></el-table-column>
    <el-table-column prop="id" label="学号"></el-table-column>
    <el-table-column type="selection" width="55" />
  </el-table>
  <el-pagination
    layout="prev, pager, next"
    v-model:current-page="page"
    :page-size="pageSize"
    :total="total"
    @change="refresh"
  />
  <DeleteResultDialog v-model="dr_show" :ids="dr_ids" :result="dr_result" />

</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { type StudentBrief } from '@/types'
import StudentDetail from './StudentDetail/StudentDetail.vue'
import { getStudentList, deleteStudents } from '@/api/student'
import DeleteResultDialog from '@/components/common/ResultDialog.vue'
import type { ResourceDeletion } from '@/types/api'

import { ElMessage } from 'element-plus'

const pageSize = 50

const total = ref(0)
const tableData = ref<StudentBrief[]>([])
const selectedData = ref<StudentBrief[]>([])
const page = ref(1)
const showIncQuota = ref(false)

onMounted(refresh)

async function refresh() {
  const res = await getStudentList()
  if (!res) {
    ElMessage.error('获取学生列表失败')
    return
  }
  total.value = res.students.length
  tableData.value = res.students
}

function handleSelectionChange(selection: StudentBrief[]) {
  selectedData.value = selection
}

const dr_show = ref(false)
const dr_ids = ref<string[]>([])
const dr_result = ref<ResourceDeletion>([])
async function handleDeleteSelected() {
  if (selectedData.value.length === 0) {
    return
  }
  ElMessageBox.confirm('确认删除选中的学生？')
    .then(async () => {
      dr_ids.value = selectedData.value.map((item) => item.id)
      const res = await deleteStudents(dr_ids.value)
      if (!res) {
        ElMessage.error('删除失败')
      } else {
        dr_result.value = res
        dr_show.value = true
      }
      refresh()
    })
    .catch(() => {
      // do nothing
    })
}
</script>

<style scoped>
.btn-group {
  margin-bottom: 0.5rem;
  display: flex;
  justify-content: flex-end;
}

.title {
  flex: 1;
}
</style>
