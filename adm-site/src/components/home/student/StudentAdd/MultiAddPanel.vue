<template>
  <el-card header="批量添加学生">
    <el-upload
      ref="upload"
      drag
      action="#"
      :auto-upload="false"
      :on-change="handleChange"
      :on-exceed="handleExceed"
      :on-remove="handleRemove"
      :limit="1"
    >
      <div class="el-upload__text">Drop file here or <em>click to upload</em></div>
      <template #tip>
        <el-link type="primary" :href="templateUrl" download="template.xlsx">下载模板文件</el-link>
      </template>
    </el-upload>
    <h4>添加预览</h4>
    <el-table class="tb-preview" :data="data" row-key="id" max-height="250" stripe>
      <el-table-column prop="id" label="学号" width="100"></el-table-column>
      <el-table-column prop="name" label="姓名" width="100"></el-table-column>
      <el-table-column prop="mail" label="邮箱"></el-table-column>
      <el-table-column prop="pwd" label="密码" width="100">
        <template #default="scope">
          {{ scope.row.pwd[0] + '******' + scope.row.pwd.slice(-1) }}
        </template>
      </el-table-column>
      <el-table-column prop="space_quota" label="空间配额">
        <template #default="scope">
          {{ formatBytes(scope.row.space_quota) }}
        </template>
      </el-table-column>
      <el-table-column prop="time_quota" label="时间配额">
        <template #default="scope">
          {{ formatTime(scope.row.time_quota) }}
        </template>
      </el-table-column>
    </el-table>
    <el-button type="primary" @click="handleConfirm">确认添加</el-button>
  </el-card>
  <ResultDialog
    v-model="dr_show"
    :ids="dr_ids"
    :result="dr_result"
    :title="'批量添加学生结果'"
    :failure-msg="'学号已存在'"
  />
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import { addStudents, type StudentCreationParams } from '@/api/student'
import * as XLSX from 'xlsx'
import { formatBytes, formatTime } from '@/utils'
import { genFileId, type UploadFile, type UploadInstance, type UploadRawFile } from 'element-plus'
import ResultDialog from '@/components/common/ResultDialog.vue'
import type { ResourceDeletion } from '@/types/api'

const upload = ref<UploadInstance>()
const templateUrl = getTemplateUrl()
const data = ref<StudentCreationParams[]>([])
const dr_show = ref(false)
const dr_ids = ref<string[]>([])
const dr_result = ref<ResourceDeletion>([])

function validateRow(row: string[]) {
  if (!row[0] || row[0].length !== 8 || !/^[0-9]+$/.test(row[0])) {
    return '学号格式错误'
  }
  if (!row[1] || row[1].length > 128) {
    return '姓名格式错误'
  }
  if (!row[2] || !/\S+@\S+\.\S+/.test(row[2])) {
    return '邮箱格式错误'
  }
  if (!row[3] || row[3].length < 6 || row[3].length > 128) {
    return '密码格式错误'
  }
  if (!row[4] || !/^[0-9]+$/.test(row[4])) {
    return '空间配额格式错误'
  }
  if (!row[5] || !/^[0-9]+$/.test(row[5])) {
    return '时间配额格式错误'
  }
  return true
}

async function handleChange(file: UploadFile) {
  if (!file.raw) {
    // TODO: handle error
    return
  }
  const fileContent = await file.raw.arrayBuffer()
  const workbook = XLSX.read(fileContent, { type: 'array' })
  const sheetName = workbook.SheetNames[0]
  const sheet = workbook.Sheets[sheetName]
  const rows = XLSX.utils.sheet_to_json(sheet, { header: 1 }).slice(1) as string[][]
  data.value = []
  for (const row of rows) {
    const result = validateRow(row)
    if (result === true) {
      const parsedRow = {
        id: row[0],
        name: row[1],
        mail: row[2],
        pwd: row[3],
        space_quota: parseInt(row[4]),
        time_quota: parseInt(row[5]),
      }
      data.value.push(parsedRow)
    } else {
      data.value = []
      upload.value!.clearFiles()
      ElMessage.error(`第${rows.indexOf(row) + 1}行${result}，请检查后重试。`)
      return
    }
  }
}

function handleExceed(files: File[]) {
  upload.value!.clearFiles()
  const file = files[0] as UploadRawFile
  file.uid = genFileId()
  upload.value!.handleStart(file)
}

function handleRemove() {
  data.value = []
}

async function handleConfirm() {
  if (data.value.length === 0) {
    ElMessage.error('请先上传学生信息。')
    return
  }
  const result = await addStudents(data.value)
  if (!result) {
    ElMessage.error('网络错误')
    return
  } else {
    dr_ids.value = data.value.map((item) => item.id)
    dr_result.value = result
    dr_show.value = true
  }
}

function getTemplateUrl() {
  const data = [
    ['学号', '姓名', '邮箱', '密码', '空间配额（字节）', '时间配额（秒）'],
    ['00000001', '张三', 'zhangsan@example.com', '123456', '1073741824', '86400'],
  ]

  const wb = XLSX.utils.book_new()
  const ws = XLSX.utils.aoa_to_sheet(data)
  XLSX.utils.book_append_sheet(wb, ws, '用户信息')

  const wbout = XLSX.write(wb, {
    bookType: 'xlsx',
    type: 'array',
  })
  const file = new File([wbout], 'template.xlsx', { type: 'application/octet-stream' })
  return URL.createObjectURL(file)
}
</script>

<style scoped>
.tb-preview {
  margin: 1rem 0;
}
</style>
