<script setup lang="ts">

// 配置好插件后，它们会自动可用。
import {ElMessage} from "element-plus";

const message = () => {
  ElMessage.success('环境配置成功！Element Plus 已就绪。')
}
</script>

<template>
  <div class="container">
    <h1>Vue 3 + Vite + Element Plus</h1>
    <el-button type="primary" @click="message">点击测试</el-button>
  </div>
</template>

<style scoped>
.container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
}
</style>
