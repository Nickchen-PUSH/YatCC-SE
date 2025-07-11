<template>
  <h2>邮箱列表</h2>
  <el-form ref="form" :model="newMail" label-width="100px" :inline="true">
    <el-form-item label="添加邮箱">
      <el-input v-model="newMail" placeholder="请输入新邮箱"></el-input>
    </el-form-item>
    <el-form-item>
      <el-button type="primary" @click="addMail">添加</el-button>
    </el-form-item>
  </el-form>
  <ListContainer
    v-model="items"
    :filter-fn="(item: MailItem, searchText: string) => item.mail.includes(searchText)"
  >
    <template #header-actions>
      <el-button type="danger"> 删除 </el-button>
    </template>
    <template #item-title="{ item }">
      <span>{{ item.mail }}</span>
    </template>
    <template #item-actions="{ item }">
      <el-button type="danger"> 删除 </el-button>
    </template>
  </ListContainer>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { addAdminMail, getAdminMails } from '@/api/admin'

interface MailItem {
  id: number
  selected: boolean
  showDetails: boolean
  mail: string
}

const items = ref<MailItem[]>([])
const newMail = ref('')

onMounted(() => {
  // items.value = mockAdminData.map((item) => ({
  //   id: items.value.length + 1,
  //   selected: false,
  //   showDetails: false,
  //   mail: item.mail,
  // }))
  getAdminMails().then((res) => {
    items.value = res.map((item) => ({
      id: items.value.length + 1,
      selected: false,
      showDetails: false,
      mail: item,
    }))
  })
})

const addMail = () => {
  addAdminMail(newMail.value).then((res) => {
    if (res == 'Ok') {
      items.value.push({
        id: items.value.length + 1,
        selected: false,
        showDetails: false,
        mail: newMail.value,
      })
      newMail.value = ''
    } else {
      alert('添加失败')
    }
  })
}
</script>

<style scoped></style>
