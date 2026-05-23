<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { RouterLink } from 'vue-router'
import { storeToRefs } from 'pinia'

import { useAppStore } from '@/stores/app'

defineProps<{
  active?: 'projects' | 'settings' | 'knowledge'
}>()

const appStore = useAppStore()
const { servicesStatusLevel, servicesStatusTitle } = storeToRefs(appStore)

const HEALTH_POLL_MS = 30_000
let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  appStore.fetchHealth()
  pollTimer = setInterval(() => {
    appStore.fetchHealth()
  }, HEALTH_POLL_MS)
})

onUnmounted(() => {
  if (null != pollTimer) {
    clearInterval(pollTimer)
  }
})
</script>

<template>
  <header class="ui-header">
    <RouterLink to="/" class="ui-logo">House<span>DIY</span></RouterLink>
    <nav class="ui-tabs">
      <RouterLink to="/" :class="{ active: active === 'projects' }">项目</RouterLink>
      <RouterLink to="/knowledge" :class="{ active: active === 'knowledge' }">知识库</RouterLink>
      <RouterLink to="/settings" :class="{ active: active === 'settings' }">系统监控</RouterLink>
    </nav>
    <div class="ui-header-right">
      <RouterLink
        to="/settings"
        class="status-led-link"
        :title="servicesStatusTitle"
        aria-label="系统服务状态"
      >
        <span class="status-led" :class="servicesStatusLevel" />
      </RouterLink>
    </div>
  </header>
</template>

<style scoped>
.status-led-link {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  text-decoration: none;
}

.status-led {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-led.ok {
  background: #8fd4a8;
  box-shadow: 0 0 8px rgba(143, 212, 168, 0.75);
}

.status-led.partial {
  background: #d9b44a;
  box-shadow: 0 0 8px rgba(217, 180, 74, 0.55);
  animation: led-blink-slow 1.6s ease-in-out infinite;
}

.status-led.offline {
  background: #d48f8f;
  box-shadow: 0 0 8px rgba(212, 143, 143, 0.55);
  animation: led-blink-fast 0.75s ease-in-out infinite;
}

.status-led.unknown {
  background: #666;
  opacity: 0.7;
}

@keyframes led-blink-fast {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.2;
  }
}

@keyframes led-blink-slow {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.35;
  }
}
</style>
