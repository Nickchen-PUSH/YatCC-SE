<script setup lang="ts">
import StatusPanel from '@/components/StatusPanel/StatusPanel.vue';
import UserInfoPanel from '@/components/UserInfoPanel/UserInfoPanel.vue';


</script>

<template>
  <div class="flex py-26">
    <div class="m-auto flex gap-1">
      <UserInfoPanel/>
      <StatusPanel/>
    </div>

  </div>
</template>
