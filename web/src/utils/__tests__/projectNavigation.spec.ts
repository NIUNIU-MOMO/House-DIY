import { describe, expect, it, vi } from 'vitest'

import {
  isStepReachable,
  resolveMaxCompletedStepIndex,
  resolveProjectEntry,
  statusToStep,
  stepIndex,
  stepToRouteName,
} from '@/utils/projectNavigation'

vi.mock('@/api/client', () => ({
  api: {
    getProject: vi.fn(),
    getFloorplan: vi.fn(),
  },
}))

import { api } from '@/api/client'

describe('projectNavigation', () => {
  it('maps delivered status to preview route', () => {
    expect(statusToStep('delivered')).toBe('preview')
    expect(stepToRouteName('preview')).toBe('delivery-overview')
  })

  it('opens delivered project on delivery overview', async () => {
    vi.mocked(api.getProject).mockResolvedValue({
      id: 2,
      name: '测试',
      status: 'delivered',
      created_at: '',
      updated_at: '',
    })

    const route = await resolveProjectEntry(2)
    expect(route).toEqual({ name: 'delivery-overview', params: { id: 2 } })
  })

  it('opens review project on editor', async () => {
    vi.mocked(api.getProject).mockResolvedValue({
      id: 3,
      name: '测试',
      status: 'review',
      created_at: '',
      updated_at: '',
    })

    const route = await resolveProjectEntry(3)
    expect(route).toEqual({ name: 'floorplan-editor', params: { id: 3 } })
  })

  it('opens draft with rooms on editor', async () => {
    vi.mocked(api.getProject).mockResolvedValue({
      id: 4,
      name: '测试',
      status: 'draft',
      created_at: '',
      updated_at: '',
    })
    vi.mocked(api.getFloorplan).mockResolvedValue({
      status: 'draft',
      scale: null,
      walls: [],
      rooms: [{ id: 'r1', name: '客厅', polygon: [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }] }],
      openings: [],
      source_url: '/x.png',
    })

    const route = await resolveProjectEntry(4)
    expect(route).toEqual({ name: 'floorplan-editor', params: { id: 4 } })
  })

  it('allows all steps for delivered project', async () => {
    vi.mocked(api.getProject).mockResolvedValue({
      id: 2,
      name: '测试',
      status: 'delivered',
      created_at: '',
      updated_at: '',
    })

    const max = await resolveMaxCompletedStepIndex(2)
    expect(max).toBe(stepIndex('preview'))
    expect(isStepReachable('upload', max)).toBe(true)
    expect(isStepReachable('preview', max)).toBe(true)
    expect(isStepReachable('design', max)).toBe(true)
  })

  it('blocks preview for review project', async () => {
    vi.mocked(api.getProject).mockResolvedValue({
      id: 5,
      name: '测试',
      status: 'review',
      created_at: '',
      updated_at: '',
    })

    const max = await resolveMaxCompletedStepIndex(5)
    expect(isStepReachable('review', max)).toBe(true)
    expect(isStepReachable('design', max)).toBe(false)
  })
})
