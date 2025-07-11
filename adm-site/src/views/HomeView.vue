<template>
  <el-container class="container">
    <el-header class="card">管理员面板</el-header>
    <el-container class="card">
      <el-aside class="sidebar">
        <el-menu default-active="student-list" router>
          <el-sub-menu index="student">
            <template #title> 学生管理 </template>
            <el-menu-item index="student-list"> 查看学生 </el-menu-item>
            <el-menu-item index="student-add"> 增加学生 </el-menu-item>
          </el-sub-menu>
          <el-menu-item index="tasker"> 任务管理 </el-menu-item>
          <el-menu-item index="codespace"> 代码空间管理 </el-menu-item>
          <el-menu-item index="account"> API-KEY 管理 </el-menu-item>
          <el-menu-item index="notification"> 通知管理 </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts"></script>

<style scoped>
.container {
  height: 100vh;
  max-width: 1200px;
  margin: 0 auto;
}

.sidebar {
  width: 20%;
  min-width: 8rem;
  max-width: 12rem;
}
</style>
