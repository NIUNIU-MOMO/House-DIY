import { describe, expect, it } from 'vitest'

import {
  insertVertexOnEdge,
  removeVertexFromPolygon,
  applyPolygonToRoom,
} from '@/components/FloorPlanEditor/usePolygonEdit'
import type { FloorWall } from '@/types/floorplan'

describe('usePolygonEdit', () => {
  const walls: FloorWall[] = [
    { id: 'w1', points: [{ x: 0, y: 0 }, { x: 200, y: 0 }] },
  ]

  const rectangle = [
    { x: 0, y: 0 },
    { x: 100, y: 0 },
    { x: 100, y: 100 },
    { x: 0, y: 100 },
  ]

  it('insertVertexOnEdge adds snapped midpoint', () => {
    const next = insertVertexOnEdge(rectangle, 0, walls)
    expect(next).not.toBeNull()
    expect(next).toHaveLength(5)
    expect(next![1]).toEqual({ x: 50, y: 0 })
  })

  it('removeVertexFromPolygon rejects when only 3 vertices remain', () => {
    const triangle = rectangle.slice(0, 3)
    expect(removeVertexFromPolygon(triangle, 0)).toBeNull()
  })

  it('removeVertexFromPolygon removes vertex', () => {
    const next = removeVertexFromPolygon(rectangle, 1)
    expect(next).toHaveLength(3)
  })

  it('applyPolygonToRoom recalculates area', () => {
    const room = applyPolygonToRoom(
      { id: 'r1', name: '客厅', polygon: rectangle, area: 1 },
      rectangle,
      100,
    )
    expect(room.area).toBe(1)
  })
})
