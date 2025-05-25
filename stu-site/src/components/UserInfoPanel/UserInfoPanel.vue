<script setup lang="ts">
import { onMounted, ref } from 'vue'
import EditInfoDialog from './EditInfoDialog.vue'
import ChangePasswordDialog from './ChangePasswordDialog.vue'
import { clearToken } from '@/composables/auth'
import router from '@/routes'
import { getUserInfo ,updateUserInfo} from '@/composables/api/userinfo'
import type { UserInfo } from '@/types'

const userInfo = ref({
  mail: '',
  name: '',
})


async function fetchUserInfo() {
  const res = await getUserInfo()
  if (!res) {
    return false
  }
  userInfo.value.mail = res.mail
  userInfo.value.name = res.name
  return true
}

onMounted(() => {
  fetchUserInfo()
})

async function handleUpdateUserInfo(data: UserInfo) {
  const res = await updateUserInfo(data)
    if (res === 'Ok') {
      ElMessage.success('个人信息修改成功')
      await fetchUserInfo()
      console.log('个人信息修改成功')
      editDialogRef.value?.closeDialog()
    }else{
      ElMessage.error('个人信息修改失败')

    }
}

const editDialogRef = ref<InstanceType<typeof EditInfoDialog>>()
const pwdDialogRef = ref<InstanceType<typeof ChangePasswordDialog>>()
// 处理信息更新


const handleLogout = () => {
  clearToken()
  router.push('/login')
}
</script>
<template>
  <el-card class="max-w-600px mx-auto shadow-lg dark:bg-#2d2d2d">
    <template #header>
      <div class="flex items-center justify-between">
        <h3 class="text-18px font-bold">个人信息</h3>

      </div>
    </template>
    <div class="flex h-268px">
      <div class="my-a flex-col space-y-6 flex-1">
        <div class="flex items-center">
          <label class="text-gray-500 dark:text-gray-400 flex items-center">
            <div class="i-mdi:account mr-1 text-20px" />
            姓名：
          </label>
          <span class="text-16px">{{ userInfo.name }}</span>
        </div>
        <div class="flex items-center">
          <label class="text-gray-500 dark:text-gray-400 flex items-center">
            <div class="i-mdi:email mr-1 text-20px" />
            邮箱：
          </label>
          <span class="text-16px">{{ userInfo.mail }}</span>
        </div>
      </div>
    </div>
    <template #footer>
      <div class="flex justify-end space-x-4">
        <el-button
          type="primary"
          @click="editDialogRef?.openDialog(userInfo)"
        >
          编辑信息
        </el-button>
        <el-button @click="pwdDialogRef?.openDialog()">
          修改密码
        </el-button>
        <el-button type="danger" @click="handleLogout">
          退出登录
        </el-button>
      </div>
    </template>
    <EditInfoDialog ref="editDialogRef" @updateInfo="handleUpdateUserInfo"/>
    <ChangePasswordDialog ref="pwdDialogRef" />
  </el-card>
</template>
