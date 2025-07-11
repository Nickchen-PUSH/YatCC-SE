<template>
  <SingleAddPanel class="card" />
  <MultiAddPanel class="card" />
</template>

<script setup lang="ts">
import MultiAddPanel from './MultiAddPanel.vue'
import SingleAddPanel from './SingleAddPanel.vue'
</script>

<style scoped>
.card {
  margin-bottom: 0.5rem;
}
</style>
