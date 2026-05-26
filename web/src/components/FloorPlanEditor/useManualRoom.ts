import type { Ref } from 'vue'

import {
  buildRoomName,
  computeRoomArea,
  defaultPolygonAt,
  nextRoomId,
  type RoomTypeKey,
} from '@/constants/roomTypes'
import type { FloorPlanData, FloorPoint, FloorRoom } from '@/types/floorplan'

export function useManualRoom(floorplan: Ref<FloorPlanData | null>) {
  function addRoomAt(typeKey: RoomTypeKey, center: FloorPoint): string | null {
    if (!floorplan.value) {
      return null
    }
    const sourceWidth = floorplan.value.source_width ?? 800
    const sourceHeight = floorplan.value.source_height ?? 600
    const polygon = defaultPolygonAt(center, sourceWidth, sourceHeight)
    const id = nextRoomId(floorplan.value.rooms)
    const name = buildRoomName(typeKey, floorplan.value.rooms)
    const area = computeRoomArea(polygon, floorplan.value.scale)
    const room: FloorRoom = { id, name, polygon, area }
    floorplan.value = {
      ...floorplan.value,
      rooms: [...floorplan.value.rooms, room],
    }
    return id
  }

  function removeRoom(roomId: string): boolean {
    if (!floorplan.value || floorplan.value.rooms.length <= 1) {
      return false
    }
    floorplan.value = {
      ...floorplan.value,
      rooms: floorplan.value.rooms.filter((room) => room.id !== roomId),
    }
    return true
  }

  return { addRoomAt, removeRoom }
}
