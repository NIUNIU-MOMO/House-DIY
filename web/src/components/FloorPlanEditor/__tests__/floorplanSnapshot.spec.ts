import { describe, expect, it } from 'vitest'
import { reactive } from 'vue'

import {
  cloneFloorplanSnapshot,
  floorplansEqual,
} from '@/components/FloorPlanEditor/floorplanSnapshot'
import type { FloorPlanData } from '@/types/floorplan'

function samplePlan(): FloorPlanData {
  return {
    scale: 100,
    status: 'draft',
    walls: [{ id: 'w1', points: [{ x: 0, y: 0 }, { x: 100, y: 0 }] }],
    rooms: [
      {
        id: 'r1',
        name: '客厅',
        polygon: [
          { x: 0, y: 0 },
          { x: 100, y: 0 },
          { x: 100, y: 100 },
          { x: 0, y: 100 },
        ],
        area: 25,
      },
    ],
    openings: [],
    source_width: 800,
    source_height: 600,
  }
}

describe('floorplanSnapshot', () => {
  it('cloneFloorplanSnapshot returns deep equal copy', () => {
    const original = samplePlan()
    const cloned = cloneFloorplanSnapshot(original)
    expect(cloned).toEqual(original)
    expect(cloned).not.toBe(original)
    cloned.rooms[0]!.name = '主卧'
    expect(original.rooms[0]?.name).toBe('客厅')
  })

  it('cloneFloorplanSnapshot works on vue reactive proxy', () => {
    const reactivePlan = reactive(samplePlan())
    const cloned = cloneFloorplanSnapshot(reactivePlan)
    expect(cloned).toEqual(samplePlan())
    expect(cloned).not.toBe(reactivePlan)
  })

  it('floorplansEqual detects polygon changes', () => {
    const a = samplePlan()
    const b = cloneFloorplanSnapshot(a)
    expect(floorplansEqual(a, b)).toBe(true)
    b.rooms[0]!.polygon[0]!.x = 5
    expect(floorplansEqual(a, b)).toBe(false)
  })
})
