<template>
  <div class="header-container">
    <span class="header-left">
      <el-input
        v-model="searchText"
        placeholder="搜索"
        style="margin-right: 10px; max-width: 200px"
      ></el-input>
      <el-button type="primary" @click="handelSearch" :icon="Search">搜索</el-button>
      <el-button type="primary" @click="handleSelectAll">
        {{ selectAll.valueOf() ? '全选' : '取消' }}
      </el-button>
    </span>
    <span class="header-right">
      <slot name="header-actions"></slot>
    </span>
  </div>
  <el-divider />
  <div v-for="item in pageItems" :key="item.id">
    <el-card style="margin-bottom: 0.5rem">
      <el-row>
        <span>
          <el-checkbox v-model="item.selected" size="large" style="margin-right: 10px" />
        </span>
        <span style="display: flex; align-items: center">
          <slot name="item-title" :item="item"></slot>
        </span>
        <span style="display: flex; justify-content: flex-end; margin-left: auto">
          <el-button
            v-if="$slots['item-details']"
            class="item-details-btn"
            @click="item.showDetails = !item.showDetails"
            >{{ item.showDetails ? '收起' : '展开' }}</el-button
          >
          <slot name="item-actions" :item="item"></slot>
        </span>
      </el-row>
      <div v-if="item.showDetails" style="margin: 1rem 1.5rem 0">
        <slot name="item-details" :item="item"></slot>
      </div>
    </el-card>
  </div>
  <el-pagination
    :hide-on-single-page="true"
    :page-size="pageSize"
    :total="filteredItems.length"
    v-model:current-page="currentPage"
    layout="prev, pager, next"
  />
</template>

<script setup lang="ts">
import { Search } from '@element-plus/icons-vue'
import { computed, ref } from 'vue'

const selectAll = ref(true)

interface Item {
  id: number | string // id 是必需的，类型可以是数字或字符串
  selected: boolean
  showDetails: boolean
  [key: string]: any // 其他属性可以是任意键值对
}

const pageSize = 10

const props = defineProps<{
  filterFn: (item: Item, keyword: string) => boolean
}>()

const items = defineModel<Item[]>({ required: true })

const searchText = ref('')
const currentPage = ref(1)
const filteredItems = computed(() => {
  return items.value.filter((item) => props.filterFn(item, searchText.value))
})
const pageItems = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return filteredItems.value.slice(start, end)
})

const handleSelectAll = () => {
  const allSelected = filteredItems.value.every((item) => item.selected)
  selectAll.value = !selectAll.value
  filteredItems.value.forEach((item) => {
    item.selected = !allSelected
  })
}

const handelSearch = () => {
  // TODO: 搜索
}
</script>

<style scoped>
.header-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 1rem;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: flex-end;
}
</style>
