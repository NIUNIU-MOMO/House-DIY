import type { FloorPoint, FloorWall } from '@/types/floorplan'

const DEFAULT_SEGMENT_THRESHOLD = 12
const DEFAULT_CORNER_THRESHOLD = 10
const CORNER_DEDUPE_DISTANCE = 2

export type SnapKind = 'corner' | 'segment' | 'none'

export interface SnapAnnotationOptions {
  segmentThreshold?: number
  cornerThreshold?: number
  cornerSnapEnabled?: boolean
  skipSnap?: boolean
}

export interface SnapAnnotationResult {
  point: FloorPoint
  kind: SnapKind
}

function distance(a: FloorPoint, b: FloorPoint): number {
  return Math.hypot(a.x - b.x, a.y - b.y)
}

function projectPointOnSegment(
  point: FloorPoint,
  start: FloorPoint,
  end: FloorPoint,
): FloorPoint {
  const dx = end.x - start.x
  const dy = end.y - start.y
  const lengthSq = dx * dx + dy * dy
  if (lengthSq <= 0) {
    return { ...start }
  }
  const t = Math.max(0, Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / lengthSq))
  return {
    x: start.x + t * dx,
    y: start.y + t * dy,
  }
}

function dedupePoints(points: FloorPoint[], minDistance = CORNER_DEDUPE_DISTANCE): FloorPoint[] {
  const result: FloorPoint[] = []
  for (const point of points) {
    const duplicate = result.some((existing) => distance(existing, point) < minDistance)
    if (!duplicate) {
      result.push(point)
    }
  }
  return result
}

/**
 * 两线段求交点（含端点，排除平行）
 */
export function segmentIntersection(
  a1: FloorPoint,
  a2: FloorPoint,
  b1: FloorPoint,
  b2: FloorPoint,
): FloorPoint | null {
  const d1x = a2.x - a1.x
  const d1y = a2.y - a1.y
  const d2x = b2.x - b1.x
  const d2y = b2.y - b1.y
  const denom = d1x * d2y - d1y * d2x
  if (Math.abs(denom) < 1e-10) {
    return null
  }
  const t = ((b1.x - a1.x) * d2y - (b1.y - a1.y) * d2x) / denom
  const u = ((b1.x - a1.x) * d1y - (b1.y - a1.y) * d1x) / denom
  if (t < 0 || t > 1 || u < 0 || u > 1) {
    return null
  }
  return { x: a1.x + t * d1x, y: a1.y + t * d1y }
}

function wallSegments(walls: FloorWall[]): Array<[FloorPoint, FloorPoint]> {
  const segments: Array<[FloorPoint, FloorPoint]> = []
  for (const wall of walls) {
    if (wall.points.length < 2) {
      continue
    }
    const start = wall.points[0]
    const end = wall.points[1]
    if (!start || !end) {
      continue
    }
    segments.push([start, end])
  }
  return segments
}

/**
 * 收集墙端点与墙段交点，供角点吸附
 */
export function collectWallCorners(walls: FloorWall[]): FloorPoint[] {
  const segments = wallSegments(walls)
  const corners: FloorPoint[] = []
  for (const [start, end] of segments) {
    corners.push({ ...start }, { ...end })
  }
  for (let i = 0; i < segments.length; i += 1) {
    for (let j = i + 1; j < segments.length; j += 1) {
      const segA = segments[i]
      const segB = segments[j]
      if (!segA || !segB) {
        continue
      }
      const hit = segmentIntersection(segA[0], segA[1], segB[0], segB[1])
      if (hit) {
        corners.push(hit)
      }
    }
  }
  return dedupePoints(corners)
}

function snapToSegment(
  point: FloorPoint,
  walls: FloorWall[],
  threshold: number,
): { point: FloorPoint; distance: number } | null {
  let bestPoint = point
  let bestDistance = threshold
  for (const wall of walls) {
    if (wall.points.length < 2) {
      continue
    }
    const start = wall.points[0]
    const end = wall.points[1]
    if (!start || !end) {
      continue
    }
    const projected = projectPointOnSegment(point, start, end)
    const dist = distance(point, projected)
    if (dist < bestDistance) {
      bestDistance = dist
      bestPoint = projected
    }
  }
  if (bestPoint === point) {
    return null
  }
  return { point: bestPoint, distance: bestDistance }
}

function snapToCorner(
  point: FloorPoint,
  corners: FloorPoint[],
  threshold: number,
): { point: FloorPoint; distance: number } | null {
  let bestPoint = point
  let bestDistance = threshold
  for (const corner of corners) {
    const dist = distance(point, corner)
    if (dist < bestDistance) {
      bestDistance = dist
      bestPoint = corner
    }
  }
  if (bestPoint === point) {
    return null
  }
  return { point: bestPoint, distance: bestDistance }
}

/**
 * 标注点吸附：角点优先，其次墙线段
 */
export function snapAnnotationPoint(
  point: FloorPoint,
  walls: FloorWall[],
  options: SnapAnnotationOptions = {},
): SnapAnnotationResult {
  if (options.skipSnap) {
    return { point, kind: 'none' }
  }

  const segmentThreshold = options.segmentThreshold ?? DEFAULT_SEGMENT_THRESHOLD
  const cornerThreshold = options.cornerThreshold ?? DEFAULT_CORNER_THRESHOLD
  const cornerSnapEnabled = options.cornerSnapEnabled ?? true

  if (cornerSnapEnabled && walls.length) {
    const corners = collectWallCorners(walls)
    const cornerHit = snapToCorner(point, corners, cornerThreshold)
    if (cornerHit) {
      return { point: cornerHit.point, kind: 'corner' }
    }
  }

  const segmentHit = snapToSegment(point, walls, segmentThreshold)
  if (segmentHit) {
    return { point: segmentHit.point, kind: 'segment' }
  }

  return { point, kind: 'none' }
}

/**
 * 将顶点吸附到最近的墙线段（FR-E4）
 */
export function snapPointToWalls(
  point: FloorPoint,
  walls: FloorWall[],
  threshold = DEFAULT_SEGMENT_THRESHOLD,
): FloorPoint {
  return snapAnnotationPoint(point, walls, { segmentThreshold: threshold }).point
}

function segmentsCross(
  a1: FloorPoint,
  a2: FloorPoint,
  b1: FloorPoint,
  b2: FloorPoint,
): boolean {
  return segmentIntersection(a1, a2, b1, b2) != null
}

function edgesAreAdjacent(i: number, j: number, count: number): boolean {
  if (i === j) {
    return true
  }
  if (Math.abs(i - j) === 1) {
    return true
  }
  return (i === 0 && j === count - 1) || (j === 0 && i === count - 1)
}

/**
 * 检测多边形是否为简单多边形（无自交叉）
 */
export function isSimplePolygon(points: FloorPoint[]): boolean {
  if (points.length < 3) {
    return false
  }
  const n = points.length
  for (let i = 0; i < n; i += 1) {
    const a1 = points[i]!
    const a2 = points[(i + 1) % n]!
    for (let j = i + 1; j < n; j += 1) {
      if (edgesAreAdjacent(i, j, n)) {
        continue
      }
      const b1 = points[j]!
      const b2 = points[(j + 1) % n]!
      if (segmentsCross(a1, a2, b1, b2)) {
        return false
      }
    }
  }
  return true
}

export function previewSnapPoint(
  point: FloorPoint,
  walls: FloorWall[],
  options: SnapAnnotationOptions = {},
): SnapAnnotationResult {
  return snapAnnotationPoint(point, walls, options)
}
