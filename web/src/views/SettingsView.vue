<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'

import AppHeader from '@/components/AppHeader.vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const { health, loading, error } = storeToRefs(appStore)

function serviceLabel(name: string, value?: string) {
  if (name === 'vault') {
    return value === 'ready' ? '已就绪' : '未找到'
  }
  return value === 'online' ? '运行中' : '离线'
}

function isOk(name: string, value?: string) {
  if (name === 'vault') {
    return value === 'ready'
  }
  return value === 'online'
}

onMounted(() => {
  appStore.fetchHealth()
})
</script>

<template>
  <div>
    <AppHeader active="settings" />
    <div class="ui-page">
      <div class="page-head">
        <div>
          <h2>系统状态与设置</h2>
          <p class="muted">本地服务健康检查 · 配置只读预览</p>
        </div>
        <button type="button" class="btn ghost" :disabled="loading" @click="appStore.fetchHealth()">
          刷新状态
        </button>
      </div>

      <p v-if="error" class="muted" style="color: #d48f8f; margin-bottom: 1rem">{{ error }}</p>

      <div v-if="health" class="service-grid">
        <div v-for="(value, key) in health.services" :key="key" class="service-card">
          <h3>
            <span class="status-dot" :class="isOk(String(key), value) ? 'ok' : 'off'" />
            {{ key }}
          </h3>
          <p class="muted">{{ serviceLabel(String(key), value) }}</p>
        </div>
      </div>

      <div v-else-if="loading" class="empty-state">
        <p>正在检测服务状态…</p>
      </div>
    </div>
  </div>
</template>
