import type { FloorPoint, FloorWall } from '@/types/floorplan'

const DEFAULT_SNAP_THRESHOLD = 12

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

/**
 * 将顶点吸附到最近的墙线段（FR-E4）
 */
export function snapPointToWalls(
  point: FloorPoint,
  walls: FloorWall[],
  threshold = DEFAULT_SNAP_THRESHOLD,
): FloorPoint {
  if (!walls.length) {
    return point
  }

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

  return bestPoint
}
