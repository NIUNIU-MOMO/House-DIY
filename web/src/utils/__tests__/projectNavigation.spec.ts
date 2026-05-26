import { describe, expect, it, vi } from 'vitest'

import {
  isStepReachable,
  maxStepToProjectStep,
  resolveMaxCompletedStepIndex,
  resolveProjectEntry,
  resolveReachableStepIndex,
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
  it('maps max_step preview to delivery route', () => {
    expect(maxStepToProjectStep('preview')).toBe('preview')
    expect(stepToRouteName('preview')).toBe('delivery-overview')
  })

  it('opens project by max_step', async () => {
    vi.mocked(api.getProject).mockResolvedValue({
      id: 2,
      name: '测试',
      status: 'delivered',
      max_step: 'preview',
      created_at: '',
      updated_at: '',
    })

    const route = await resolveProjectEntry(2)
    expect(route).toEqual({ name: 'delivery-overview', params: { id: 2 } })
  })

  it('allows design step when annotation confirmed', () => {
    const max = resolveReachableStepIndex({
      id: 1,
      name: 'x',
      status: 'designing',
      max_step: 'annotate',
      annotation_confirmed_at: '2026-01-01T00:00:00Z',
      created_at: '',
      updated_at: '',
    })
    expect(isStepReachable('design', max)).toBe(true)
    expect(isStepReachable('preview', max)).toBe(false)
  })

  it('resolveMaxCompletedStepIndex uses max_step', async () => {
    vi.mocked(api.getProject).mockResolvedValue({
      id: 3,
      name: '测试',
      status: 'review',
      max_step: 'annotate',
      created_at: '',
      updated_at: '',
    })

    const max = await resolveMaxCompletedStepIndex(3)
    expect(max).toBe(stepIndex('annotate'))
    expect(isStepReachable('annotate', max)).toBe(true)
    expect(isStepReachable('design', max)).toBe(false)
  })
})
