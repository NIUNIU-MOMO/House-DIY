import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import HomeView from '@/views/HomeView.vue'

vi.mock('@/api/client', () => ({
  api: {
    health: vi.fn().mockResolvedValue({
      status: 'ok',
      services: { omlx: 'online', comfyui: 'online', vault: 'ready' },
    }),
    listProjects: vi.fn().mockResolvedValue([
      {
        id: 1,
        name: '新建户型项目',
        status: 'draft',
        created_at: '',
        updated_at: '',
      },
      {
        id: 2,
        name: '户型图解析测试',
        status: 'delivered',
        created_at: '',
        updated_at: '',
        cover_image_url: '/api/v1/projects/2/renders/r1/image',
      },
    ]),
    createProject: vi.fn(),
    deleteProject: vi.fn(),
  },
}))

describe('HomeView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('hides default draft placeholder and shows real projects', async () => {
    const wrapper = mount(HomeView, {
      global: {
        plugins: [createPinia()],
        stubs: { RouterLink: true, AppHeader: true },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('户型图解析测试')
    expect(wrapper.text()).not.toContain('新建户型项目')
    expect(wrapper.text()).not.toContain('oMLX')
    expect(wrapper.text()).not.toContain('全部数据保存在本机')
    expect(wrapper.find('.thumb.has-cover img').attributes('src')).toBe(
      '/api/v1/projects/2/renders/r1/image',
    )
  })
})
