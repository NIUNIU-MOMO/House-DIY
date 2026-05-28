import { computed, ref } from 'vue'

import { buildRoomName, computeRoomArea, nextRoomId, type RoomTypeKey } from '@/constants/roomTypes'
import {
  isSimplePolygon,
  snapAnnotationPoint,
  type SnapAnnotationOptions,
} from '@/utils/geometry'
import type { FloorPoint, FloorRoom, FloorWall } from '@/types/floorplan'

import { MAX_POLYGON_VERTICES } from './usePolygonEdit'

export type TraceTarget = {
  typeKey: RoomTypeKey
  redrawRoomId: string | null
}

export function useTraceMode() {
  const traceTarget = ref<TraceTarget | null>(null)
  const tracePoints = ref<FloorPoint[]>([])
  const traceError = ref<string | null>(null)

  const isTraceActive = computed(() => traceTarget.value != null)

  const canCloseTrace = computed(() => tracePoints.value.length >= 3)

  function startTrace(typeKey: RoomTypeKey, redrawRoomId: string | null = null) {
    traceTarget.value = { typeKey, redrawRoomId }
    tracePoints.value = []
    traceError.value = null
  }

  function cancelTrace() {
    traceTarget.value = null
    tracePoints.value = []
    traceError.value = null
  }

  function undoTracePoint() {
    if (!tracePoints.value.length) {
      return
    }
    tracePoints.value = tracePoints.value.slice(0, -1)
    traceError.value = null
  }

  function addTracePoint(
    point: FloorPoint,
    walls: FloorWall[],
    options?: SnapAnnotationOptions,
  ): boolean {
    if (!traceTarget.value) {
      return false
    }
    if (tracePoints.value.length >= MAX_POLYGON_VERTICES) {
      traceError.value = `最多 ${MAX_POLYGON_VERTICES} 个顶点`
      return false
    }
    tracePoints.value = [...tracePoints.value, snapAnnotationPoint(point, walls, options).point]
    traceError.value = null
    return true
  }

  function closeTrace(): FloorPoint[] | null {
    if (!canCloseTrace.value) {
      traceError.value = '至少需要 3 个点才能闭合'
      return null
    }
    const polygon = [...tracePoints.value]
    if (!isSimplePolygon(polygon)) {
      traceError.value = '轮廓自交叉，请调整顶点'
      return null
    }
    traceError.value = null
    return polygon
  }

  function buildTraceRoom(
    polygon: FloorPoint[],
    existingRooms: FloorRoom[],
    scale: number | null,
  ): FloorRoom | null {
    if (!traceTarget.value) {
      return null
    }
    const { typeKey, redrawRoomId } = traceTarget.value
    if (redrawRoomId) {
      const existing = existingRooms.find((room) => room.id === redrawRoomId)
      if (!existing) {
        return null
      }
      return {
        ...existing,
        polygon,
        area: computeRoomArea(polygon, scale),
      }
    }
    const id = nextRoomId(existingRooms)
    const name = buildRoomName(typeKey, existingRooms)
    return {
      id,
      name,
      polygon,
      area: computeRoomArea(polygon, scale),
    }
  }

  return {
    traceTarget,
    tracePoints,
    traceError,
    isTraceActive,
    canCloseTrace,
    startTrace,
    cancelTrace,
    undoTracePoint,
    addTracePoint,
    closeTrace,
    buildTraceRoom,
  }
}
