<template>
  <div class="wrapper">
    <el-input class="input" v-model.number="form.GB" :rules="rule" @input="handleInput"></el-input>
    <span> GB </span>

    <el-input class="input" v-model.number="form.MB" :rules="rule" @input="handleInput"></el-input>
    <span> MB </span>

    <!-- 不需要这么细 -->
    <!-- <el-input class="input" v-model.number="form.KB" :rules="rule" @input="handleInput"></el-input>
    <span> KB </span>

    <el-input class="input" v-model.number="form.B" :rules="rule" @input="handleInput"></el-input>
    <span> B </span> -->
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
  GB: 0,
  MB: 0,
  KB: 0,
  B: 0,
})

const rule = [
  {
    type: 'number',
    min: 0,
    max: 1024,
    message: '请输入0-1024之间的数字',
    trigger: 'blur',
  },
]

function handleInput() {
  let totalBytes = 0
  let multiplier = 1
  totalBytes += form.value.B * multiplier
  multiplier *= 1024
  totalBytes += form.value.KB * multiplier
  multiplier *= 1024
  totalBytes += form.value.MB * multiplier
  multiplier *= 1024
  totalBytes += form.value.GB * multiplier
  emits('update:modelValue', totalBytes)
}

watch(
  () => props.modelValue,
  (newValue) => {
    let n = newValue
    form.value.B = n % 1024
    n = Math.floor(n / 1024)
    form.value.KB = n % 1024
    n = Math.floor(n / 1024)
    form.value.MB = n % 1024
    n = Math.floor(n / 1024)
    form.value.GB = n % 1024
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
