export interface FloorPoint {
  x: number
  y: number
}

export interface FloorWall {
  id: string
  points: FloorPoint[]
  thickness?: number
}

export interface FloorRoom {
  id: string
  name: string
  polygon: FloorPoint[]
  area?: number | null
}

export interface FloorOpening {
  id: string
  type: 'door' | 'window'
  wall_id: string
  position: number
  width: number
  connects: string[]
}

export interface FloorPlanData {
  scale: number | null
  status: string
  walls: FloorWall[]
  rooms: FloorRoom[]
  openings: FloorOpening[]
  source_url?: string | null
  source_width?: number | null
  source_height?: number | null
}

export function polygonCentroid(polygon: FloorPoint[]): FloorPoint {
  if (!polygon.length) {
    return { x: 0, y: 0 }
  }
  const sum = polygon.reduce(
    (acc, point) => ({ x: acc.x + point.x, y: acc.y + point.y }),
    { x: 0, y: 0 },
  )
  return { x: sum.x / polygon.length, y: sum.y / polygon.length }
}

export function computeViewBox(floorplan: FloorPlanData, padding = 20): string {
  if (floorplan.source_width && floorplan.source_height) {
    return `${-padding} ${-padding} ${floorplan.source_width + padding * 2} ${floorplan.source_height + padding * 2}`
  }
  const points: FloorPoint[] = []
  floorplan.walls.forEach((wall) => points.push(...wall.points))
  floorplan.rooms.forEach((room) => points.push(...room.polygon))
  if (!points.length) {
    return '0 0 400 300'
  }
  const xs = points.map((p) => p.x)
  const ys = points.map((p) => p.y)
  const minX = Math.min(...xs) - padding
  const minY = Math.min(...ys) - padding
  const maxX = Math.max(...xs) + padding
  const maxY = Math.max(...ys) + padding
  return `${minX} ${minY} ${maxX - minX} ${maxY - minY}`
}

export function scaleLabel(scale: number | null): string {
  if (!scale) {
    return '未标定'
  }
  const metersPerPixel = 1 / scale
  return `1px = ${metersPerPixel.toFixed(3)}m`
}
