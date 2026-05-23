<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { storeToRefs } from 'pinia'

import AppHeader from '@/components/AppHeader.vue'
import ServiceLogModal from '@/components/ServiceLogModal.vue'
import { type ServiceDetail } from '@/api/client'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const { health, loading, error } = storeToRefs(appStore)

const serviceDetails = ref<Record<string, ServiceDetail>>({})
const logService = ref<string | null>(null)

const serviceEntries = computed(() => {
  if (!health.value) {
    return []
  }
  return Object.entries(health.value.services).map(([key, value]) => ({
    key,
    value,
    detail: serviceDetails.value[key] ?? {
      label: key,
      web_url: '#',
      external: true,
    },
  }))
})

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

async function loadHealth() {
  await appStore.fetchHealth()
  serviceDetails.value = appStore.health?.service_details ?? {}
}

function openLogs(serviceKey: string) {
  logService.value = serviceKey
}

function closeLogs() {
  logService.value = null
}

const activeLogLabel = computed(() => {
  if (!logService.value) {
    return ''
  }
  return serviceDetails.value[logService.value]?.label ?? logService.value
})

onMounted(loadHealth)
</script>

<template>
  <div>
    <AppHeader active="settings" />
    <div class="ui-page settings-page">
      <div class="page-toolbar">
        <button
          type="button"
          class="icon-refresh-btn"
          :disabled="loading"
          title="刷新状态"
          aria-label="刷新状态"
          @click="loadHealth()"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path
              fill="currentColor"
              d="M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08a5.99 5.99 0 0 1-5.65 4c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"
            />
          </svg>
        </button>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>

      <div v-if="health" class="service-grid">
        <div v-for="item in serviceEntries" :key="item.key" class="service-card">
          <div class="service-card-head">
            <h3>
              <span class="status-dot" :class="isOk(item.key, item.value) ? 'ok' : 'off'" />
              <a
                v-if="item.detail.external"
                :href="item.detail.web_url"
                class="service-link"
                target="_blank"
                rel="noopener noreferrer"
              >
                {{ item.detail.label }}
              </a>
              <RouterLink
                v-else
                :to="item.detail.web_url"
                class="service-link"
              >
                {{ item.detail.label }}
              </RouterLink>
            </h3>
            <button type="button" class="btn sm ghost" @click="openLogs(item.key)">日志</button>
          </div>
          <p class="muted">{{ serviceLabel(item.key, item.value) }}</p>
        </div>
      </div>

      <div v-else-if="loading" class="empty-state">
        <p>正在检测服务状态…</p>
      </div>
    </div>

    <ServiceLogModal
      v-if="logService"
      :service="logService"
      :service-label="activeLogLabel"
      :open="Boolean(logService)"
      @close="closeLogs"
    />
  </div>
</template>

<style scoped>
.settings-page {
  padding-top: 0.75rem;
}

.page-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 1rem;
}

.icon-refresh-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: 1px solid #444;
  background: var(--bg-panel);
  color: #ddd;
  display: grid;
  place-items: center;
  cursor: pointer;
}

.icon-refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.icon-refresh-btn:not(:disabled):hover {
  border-color: var(--accent);
  color: var(--accent);
}

.service-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.35rem;
}

.service-card-head h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
}

.service-link {
  color: inherit;
  text-decoration: none;
}

.service-link:hover {
  color: var(--accent);
  text-decoration: underline;
}

.error-text {
  color: #d48f8f;
  margin-bottom: 1rem;
}
</style>
