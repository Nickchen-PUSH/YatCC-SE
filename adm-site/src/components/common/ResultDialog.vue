<template>
  <el-dialog v-model="isVisible" :title="title" append-to-body>
    <p>{{ successSummary }}：{{ successCount }}</p>
    <p>{{ failureSummary }}：{{ failureCount }}</p>
    <p>{{ errorSummary }}：{{ errorCount }}</p>
    <el-table :data="data" max-height="300">
      <el-table-column prop="id" :label="idName" />
      <el-table-column prop="msg" label="结果" />
      <el-table-column prop="type" label="错误类型" />
      <el-table-column prop="uuid" label="错误UUID" />
      <el-table-column prop="info" label="错误信息" />
    </el-table>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ErrorResponse, ResourceDeletion } from '@/types/api'

const isVisible = defineModel<boolean>()

interface Props {
  ids: string[]
  result: ResourceDeletion
  idName?: string
  title?: string
  successSummary?: string
  failureSummary?: string
  errorSummary?: string
  successMsg?: string
  failureMsg?: string
  errorMsg?: string
  tableGuide?: string
}

const {
  ids,
  result,
  idName = 'ID',
  title = '删除结果',
  successSummary = '成功汇总',
  failureSummary = '失败汇总',
  errorSummary = '出错汇总',
  successMsg = '成功',
  failureMsg = '失败',
  errorMsg = '出错',
} = defineProps<Props>()

interface Data {
  id: string
  msg: string
  type: string
  uuid: string
  info: string
}

const data = computed(() => {
  if (ids.length !== result.length) {
    console.warn('DeleteResultDialog: ids length is not equal to result length')
    return []
  }
  const res: Data[] = []
  for (let i = 0; i < ids.length; i++) {
    const _data: Data = {
      id: ids[i],
      msg: '',
      type: '',
      uuid: '',
      info: '',
    }
    if (typeof result[i] === 'boolean') {
      _data.msg = result[i] ? successMsg : failureMsg
    } else {
      const _result = result[i] as ErrorResponse
      _data.type = _result.type.toString()
      _data.uuid = _result.uuid
      _data.info = _result.info
      _data.msg = errorMsg
    }
    res.push(_data)
  }
  return res
})

const successCount = computed(() => {
  let count = 0
  result.forEach((item) => {
    if (typeof item === 'boolean' && item) {
      count++
    }
  })
  return count
})
const failureCount = computed(() => {
  let count = 0
  result.forEach((item) => {
    if (typeof item === 'boolean' && !item) {
      count++
    }
  })
  return count
})
const errorCount = computed(() => {
  let count = 0
  result.forEach((item) => {
    if (typeof item !== 'boolean') {
      count++
    }
  })
  return count
})
</script>

<style scoped></style>
