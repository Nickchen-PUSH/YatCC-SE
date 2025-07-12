<script setup lang="ts">

const props = defineProps<{
  text: string

}>()
const emit = defineEmits(['callback'])

const copy = () => {
  navigator.clipboard
  .writeText(props.text)
  .then(() => {
    ElMessage.success('复制成功')
  })
  .catch(() => {
    ElMessage.error('复制失败，请手动复制')
    emit('callback')
  })
}

</script>
<template>
  <button  @click="copy" class="text-16px rounded border flex p-2 border-gray-300
  cursor-pointer
  hover:bg-gray-100 transition duration-200 ease-in-out
  dark:hover:bg-gray-800 dark:border-gray-600">
    <div class="i-mdi:content-copy"/>
  </button>
</template>
