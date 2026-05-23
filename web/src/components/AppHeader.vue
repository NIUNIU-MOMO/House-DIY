<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { storeToRefs } from 'pinia'

import { useAppStore } from '@/stores/app'

defineProps<{
  active?: 'projects' | 'settings' | 'knowledge'
}>()

const appStore = useAppStore()
const { omlxOnline } = storeToRefs(appStore)
</script>

<template>
  <header class="ui-header">
    <RouterLink to="/" class="ui-logo">House<span>DIY</span></RouterLink>
    <nav class="ui-tabs">
      <RouterLink to="/" :class="{ active: active === 'projects' }">项目</RouterLink>
      <RouterLink to="/knowledge" :class="{ active: active === 'knowledge' }">知识库</RouterLink>
      <RouterLink to="/settings" :class="{ active: active === 'settings' }">设置</RouterLink>
    </nav>
    <div class="ui-header-right">
      <span class="badge offline">本地离线</span>
      <RouterLink
        to="/settings"
        class="icon-btn"
        :class="omlxOnline ? 'svc-ok' : 'svc-off'"
        title="oMLX 状态"
      >
        ●
      </RouterLink>
    </div>
  </header>
</template>
