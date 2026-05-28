import { describe, expect, it } from 'vitest'

import {
  collectWallCorners,
  isSimplePolygon,
  snapAnnotationPoint,
  snapPointToWalls,
  segmentIntersection,
} from '@/utils/geometry'
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

describe('collectWallCorners', () => {
  it('includes endpoints and intersection of crossing walls', () => {
    const walls: FloorWall[] = [
      { id: 'w1', points: [{ x: 0, y: 50 }, { x: 100, y: 50 }] },
      { id: 'w2', points: [{ x: 50, y: 0 }, { x: 50, y: 100 }] },
    ]
    const corners = collectWallCorners(walls)
    const hasIntersection = corners.some(
      (point) => Math.abs(point.x - 50) < 1 && Math.abs(point.y - 50) < 1,
    )
    expect(hasIntersection).toBe(true)
    expect(corners.length).toBeGreaterThanOrEqual(5)
  })
})

describe('segmentIntersection', () => {
  it('finds crossing point', () => {
    const hit = segmentIntersection(
      { x: 0, y: 50 },
      { x: 100, y: 50 },
      { x: 50, y: 0 },
      { x: 50, y: 100 },
    )
    expect(hit).toEqual({ x: 50, y: 50 })
  })
})

describe('snapAnnotationPoint', () => {
  const walls: FloorWall[] = [
    { id: 'h', points: [{ x: 0, y: 0 }, { x: 200, y: 0 }] },
    { id: 'v', points: [{ x: 0, y: 0 }, { x: 0, y: 200 }] },
  ]

  it('prefers corner over segment when both are in range', () => {
    const result = snapAnnotationPoint({ x: 3, y: 3 }, walls)
    expect(result.kind).toBe('corner')
    expect(result.point.x).toBeCloseTo(0, 5)
    expect(result.point.y).toBeCloseTo(0, 5)
  })

  it('returns original point when no walls', () => {
    const point = { x: 10, y: 10 }
    expect(snapAnnotationPoint(point, []).point).toEqual(point)
  })

  it('skips snap when skipSnap is true', () => {
    const point = { x: 3, y: 3 }
    const result = snapAnnotationPoint(point, walls, { skipSnap: true })
    expect(result).toEqual({ point, kind: 'none' })
  })
})

describe('isSimplePolygon', () => {
  it('accepts rectangle', () => {
    expect(
      isSimplePolygon([
        { x: 0, y: 0 },
        { x: 100, y: 0 },
        { x: 100, y: 100 },
        { x: 0, y: 100 },
      ]),
    ).toBe(true)
  })

  it('rejects bowtie polygon', () => {
    expect(
      isSimplePolygon([
        { x: 0, y: 0 },
        { x: 100, y: 100 },
        { x: 100, y: 0 },
        { x: 0, y: 100 },
      ]),
    ).toBe(false)
  })
})
