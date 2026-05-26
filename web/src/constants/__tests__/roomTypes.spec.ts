import { describe, expect, it } from 'vitest'

import {
  buildRoomName,
  defaultPolygonAt,
  nextRoomId,
  polygonArea,
} from '@/constants/roomTypes'
import type { FloorRoom } from '@/types/floorplan'

describe('nextRoomId', () => {
  it('increments from existing r ids', () => {
    const rooms: FloorRoom[] = [
      { id: 'r1', name: '客厅', polygon: [] },
      { id: 'r4', name: '卧室A', polygon: [] },
    ]
    expect(nextRoomId(rooms)).toBe('r5')
  })
})

describe('buildRoomName', () => {
  it('assigns bedroom letter suffix', () => {
    const rooms: FloorRoom[] = [{ id: 'r1', name: '卧室A', polygon: [] }]
    expect(buildRoomName('bedroom', rooms)).toBe('卧室B')
  })

  it('assigns numeric suffix for kitchen', () => {
    const rooms: FloorRoom[] = [{ id: 'r1', name: '厨房', polygon: [] }]
    expect(buildRoomName('kitchen', rooms)).toBe('厨房2')
  })

  it('uses base name when unused', () => {
    expect(buildRoomName('kitchen', [])).toBe('厨房')
  })
})

describe('defaultPolygonAt', () => {
  it('creates axis-aligned rect clamped to source bounds', () => {
    const poly = defaultPolygonAt({ x: 10, y: 10 }, 800, 600)
    expect(poly).toHaveLength(4)
    expect(poly.every((point) => point.x >= 0 && point.y >= 0)).toBe(true)
    expect(poly.every((point) => point.x <= 800 && point.y <= 600)).toBe(true)
  })

  it('stays inside when center is near edge', () => {
    const poly = defaultPolygonAt({ x: 2, y: 2 }, 800, 600)
    expect(Math.min(...poly.map((point) => point.x))).toBe(0)
    expect(Math.min(...poly.map((point) => point.y))).toBe(0)
  })
})

describe('polygonArea', () => {
  it('computes rectangle area', () => {
    const area = polygonArea([
      { x: 0, y: 0 },
      { x: 10, y: 0 },
      { x: 10, y: 5 },
      { x: 0, y: 5 },
    ])
    expect(area).toBe(50)
  })
})
