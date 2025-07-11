<template>
  <div class="wrapper">
    <el-input
      class="input"
      v-model.number="form.hour"
      :rules="rule"
      @input="handleInput"
    ></el-input>
    <span> 小时 </span>

    <el-input
      class="input"
      v-model.number="form.minute"
      :rules="rule"
      @input="handleInput"
    ></el-input>
    <span> 分钟 </span>

    <!-- 不需要这么细 -->
    <!-- <el-input class="input" v-model.number="form.second" :rules="rule" @input="handleInput"></el-input>
    <span> 秒 </span> -->
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Number,
    default: 0,
  },
})

const emits = defineEmits(['update:modelValue'])

const form = ref({
  hour: 0,
  minute: 0,
  second: 0,
})

const rule = [
  {
    type: 'number',
    min: 0,
    max: 60,
    message: '请输入0-60之间的数字',
    trigger: 'blur',
  },
]

function handleInput() {
  let totalSeconds = 0
  let multiplier = 1
  totalSeconds += form.value.second * multiplier
  multiplier *= 60
  totalSeconds += form.value.minute * multiplier
  multiplier *= 60
  totalSeconds += form.value.hour * multiplier
  emits('update:modelValue', totalSeconds)
}

watch(
  () => props.modelValue,
  (newValue) => {
    let n = newValue
    form.value.second = n % 60
    n = Math.floor(n / 60)
    form.value.minute = n % 60
    n = Math.floor(n / 60)
    form.value.hour = n % 24
  },
)
</script>

<style scoped>
.wrapper > * {
  margin-right: 0.5rem;
}

.input {
  display: inline-block;
  width: 50px;
}
</style>
