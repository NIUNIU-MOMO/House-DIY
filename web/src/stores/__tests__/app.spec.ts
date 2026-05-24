import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useAppStore } from '@/stores/app'

describe('app store servicesStatusLevel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('returns ok when all services healthy', () => {
    const store = useAppStore()
    store.health = {
      status: 'ok',
      services: { omlx: 'online', comfyui: 'online', redis: 'online', vault: 'ready' },
    }

    expect(store.servicesStatusLevel).toBe('ok')
  })

  it('returns offline when all services down', () => {
    const store = useAppStore()
    store.health = {
      status: 'ok',
      services: { omlx: 'offline', comfyui: 'offline', redis: 'offline', vault: 'missing' },
    }

    expect(store.servicesStatusLevel).toBe('offline')
  })

  it('returns partial when mixed', () => {
    const store = useAppStore()
    store.health = {
      status: 'ok',
      services: { omlx: 'online', comfyui: 'offline', redis: 'online', vault: 'ready' },
    }

    expect(store.servicesStatusLevel).toBe('partial')
  })
})
