<script setup lang="ts">
import { toggleDark } from '@/composables/utils/dark';



</script>

<template>
  <el-divider border-style="dotted"/>
  <div class="flex justify-center items-center w-full text-2xl gap-2">
    <button @click="toggleDark()"
    class="cursor-pointer select-none opacity-75
    transition duration-200 ease-in-out hover:color-[var(--el-color-primary)]">
      <div class="i-material-symbols:light-mode  dark:i-material-symbols:dark-mode">
      </div>
    </button>
    <a href="https://github.com/Nickchen-PUSH/YatCC-SE/tree/main"
    class="cursor-pointer select-none opacity-75
    transition duration-200 ease-in-out hover:color-[var(--el-color-primary)]">
      <div class="i-mdi:github">
      </div>
    </a>
  </div>
</template>
