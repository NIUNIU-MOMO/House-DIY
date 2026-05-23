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

  function isServiceOk(name: string, value?: string): boolean {
    if (name === 'vault') {
      return value === 'ready'
    }
    return value === 'online'
  }

  /** 顶栏指示灯：ok 全绿 / partial 黄闪 / offline 红快闪 / unknown 未检测 */
  const servicesStatusLevel = computed<'ok' | 'partial' | 'offline' | 'unknown'>(() => {
    if (null == health.value) {
      return error.value ? 'offline' : 'unknown'
    }

    const services = health.value.services
    const keys = ['omlx', 'comfyui', 'vault'] as const
    const okCount = keys.filter((key) => isServiceOk(key, services[key])).length

    if (okCount === keys.length) {
      return 'ok'
    }
    if (0 === okCount) {
      return 'offline'
    }
    return 'partial'
  })

  const servicesStatusTitle = computed(() => {
    const level = servicesStatusLevel.value
    if ('ok' === level) {
      return 'oMLX · ComfyUI · Vault 全部正常'
    }
    if ('partial' === level) {
      return '部分服务异常，点击查看详情'
    }
    if ('offline' === level) {
      return '服务不可用，点击查看详情'
    }
    return '正在检测服务状态…'
  })

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
    isServiceOk,
    servicesStatusLevel,
    servicesStatusTitle,
    fetchHealth,
  }
})
