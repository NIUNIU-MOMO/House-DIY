import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import { useManualRoom } from '@/components/FloorPlanEditor/useManualRoom'
import type { FloorPlanData } from '@/types/floorplan'

function basePlan(): FloorPlanData {
  return {
    scale: 100,
    status: 'draft',
    walls: [],
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
      },
    ],
    openings: [],
    source_width: 800,
    source_height: 600,
  }
}

describe('useManualRoom', () => {
  it('addRoomAt appends room and returns id', () => {
    const floorplan = ref<FloorPlanData | null>(basePlan())
    const { addRoomAt } = useManualRoom(floorplan)
    const id = addRoomAt('bedroom', { x: 200, y: 200 })
    expect(id).toBe('r2')
    expect(floorplan.value?.rooms).toHaveLength(2)
    expect(floorplan.value?.rooms[1]?.name).toMatch(/卧室/)
    expect(floorplan.value?.rooms[1]?.polygon).toHaveLength(4)
  })

  it('removeRoom blocks deleting last room', () => {
    const floorplan = ref<FloorPlanData | null>(basePlan())
    const { removeRoom } = useManualRoom(floorplan)
    expect(removeRoom('r1')).toBe(false)
    expect(floorplan.value?.rooms).toHaveLength(1)
  })

  it('removeRoom deletes when multiple rooms exist', () => {
    const floorplan = ref<FloorPlanData | null>(basePlan())
    const manual = useManualRoom(floorplan)
    manual.addRoomAt('bedroom', { x: 200, y: 200 })
    expect(manual.removeRoom('r2')).toBe(true)
    expect(floorplan.value?.rooms).toHaveLength(1)
  })
})
