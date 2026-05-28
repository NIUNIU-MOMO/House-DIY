import { computeRoomArea } from '@/constants/roomTypes'
import {
  snapAnnotationPoint,
  type SnapAnnotationOptions,
} from '@/utils/geometry'
import type { FloorPoint, FloorRoom, FloorWall } from '@/types/floorplan'

export const MAX_POLYGON_VERTICES = 32
export const MIN_POLYGON_VERTICES = 3

export function edgeMidpoint(a: FloorPoint, b: FloorPoint): FloorPoint {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }
}

export function insertVertexOnEdge(
  polygon: FloorPoint[],
  edgeIndex: number,
  walls: FloorWall[],
  options?: SnapAnnotationOptions,
): FloorPoint[] | null {
  if (polygon.length >= MAX_POLYGON_VERTICES || edgeIndex < 0 || edgeIndex >= polygon.length) {
    return null
  }
  const start = polygon[edgeIndex]
  const end = polygon[(edgeIndex + 1) % polygon.length]
  if (!start || !end) {
    return null
  }
  const mid = edgeMidpoint(start, end)
  const snapped = snapAnnotationPoint(mid, walls, options).point
  const next = [...polygon]
  next.splice(edgeIndex + 1, 0, snapped)
  return next
}

export function removeVertexFromPolygon(
  polygon: FloorPoint[],
  vertexIndex: number,
): FloorPoint[] | null {
  if (polygon.length <= MIN_POLYGON_VERTICES || vertexIndex < 0 || vertexIndex >= polygon.length) {
    return null
  }
  return polygon.filter((_, index) => index !== vertexIndex)
}

export function applyPolygonToRoom(
  room: FloorRoom,
  polygon: FloorPoint[],
  scale: number | null,
): FloorRoom {
  return {
    ...room,
    polygon,
    area: computeRoomArea(polygon, scale),
  }
}

export function updateRoomPolygon(
  rooms: FloorRoom[],
  roomId: string,
  polygon: FloorPoint[],
  scale: number | null,
): FloorRoom[] {
  return rooms.map((room) =>
    room.id === roomId ? applyPolygonToRoom(room, polygon, scale) : room,
  )
}
