import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import HomeView from '@/views/HomeView.vue'
import { useAppStore } from '@/stores/app'

vi.mock('@/api/client', () => ({
  api: {
    health: vi.fn().mockResolvedValue({
      status: 'ok',
      services: { omlx: 'online', comfyui: 'online', vault: 'ready' },
    }),
    listProjects: vi.fn().mockResolvedValue([]),
    createProject: vi.fn(),
    deleteProject: vi.fn(),
  },
}))

describe('HomeView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('shows service status from health API', async () => {
    const wrapper = mount(HomeView, {
      global: {
        plugins: [createPinia()],
        stubs: { RouterLink: true },
      },
    })

    await flushPromises()

    const store = useAppStore()
    expect(store.omlxOnline).toBe(true)
    expect(wrapper.text()).toContain('oMLX')
    expect(wrapper.text()).toContain('运行中')
  })
})
