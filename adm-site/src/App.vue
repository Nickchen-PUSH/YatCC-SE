<script setup lang="ts">
import { RouterView } from 'vue-router'
import { useDark, useToggle } from '@vueuse/core'
import { Sunny, Moon } from '@element-plus/icons-vue'

const isDark = useDark()
const toggleDark = useToggle(isDark)
</script>

<template>
  <div style="display: flex; align-items: center; justify-content: center">
    <RouterView />
    <el-button @click="toggleDark()" class="theme-btn" :icon="isDark ? Moon : Sunny" circle>
    </el-button>
  </div>
</template>

<style scoped>
.theme-btn {
  position: fixed;
  top: 10px;
  right: 10px;
}
</style>
