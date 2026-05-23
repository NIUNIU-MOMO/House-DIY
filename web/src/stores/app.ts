import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api, type HealthResponse } from '@/api/client'

export const useAppStore = defineStore('app', () => {
  const health = ref<HealthResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const omlxOnline = computed(() => health.value?.services.omlx === 'online')
  const comfyuiOnline = computed(() => health.value?.services.comfyui === 'online')
  const vaultReady = computed(() => health.value?.services.vault === 'ready')

  async function fetchHealth() {
    loading.value = true
    error.value = null
    try {
      health.value = await api.health()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Health check failed'
    } finally {
      loading.value = false
    }
  }

  return {
    health,
    loading,
    error,
    omlxOnline,
    comfyuiOnline,
    vaultReady,
    fetchHealth,
  }
})
