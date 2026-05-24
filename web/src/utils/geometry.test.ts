import { describe, expect, it } from 'vitest'

import { snapPointToWalls } from '@/utils/geometry'
import type { FloorWall } from '@/types/floorplan'

describe('snapPointToWalls', () => {
  const walls: FloorWall[] = [
    {
      id: 'w1',
      points: [
        { x: 0, y: 0 },
        { x: 200, y: 0 },
      ],
      thickness: 0.2,
    },
  ]

  it('snaps near horizontal wall', () => {
    const snapped = snapPointToWalls({ x: 100, y: 8 }, walls, 12)
    expect(snapped.x).toBeCloseTo(100, 5)
    expect(snapped.y).toBeCloseTo(0, 5)
  })

  it('keeps point when far from walls', () => {
    const point = { x: 50, y: 80 }
    const snapped = snapPointToWalls(point, walls, 12)
    expect(snapped).toEqual(point)
  })
})
