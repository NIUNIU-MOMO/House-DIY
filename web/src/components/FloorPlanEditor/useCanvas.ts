import { computed, ref } from 'vue'
import type { Ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api/client'
import {
  computeViewBox,
  polygonCentroid,
  scaleLabel,
  type FloorPlanData,
  type FloorRoom,
} from '@/types/floorplan'

export function useFloorPlanCanvas(projectId: Ref<number>) {
  const router = useRouter()
  const floorplan = ref<FloorPlanData | null>(null)
  const selectedRoomId = ref<string | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

  const viewBox = computed(() =>
    floorplan.value ? computeViewBox(floorplan.value) : '0 0 400 300',
  )

  const selectedRoom = computed(() => {
    if (!floorplan.value || !selectedRoomId.value) {
      return null
    }
    return floorplan.value.rooms.find((room) => room.id === selectedRoomId.value) ?? null
  })

  const scaleText = computed(() => scaleLabel(floorplan.value?.scale ?? null))

  async function load() {
    loading.value = true
    error.value = null
    try {
      const data = (await api.getFloorplan(projectId.value)) as FloorPlanData
      floorplan.value = data
      selectedRoomId.value = data.rooms[0]?.id ?? null
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function save() {
    if (!floorplan.value) {
      return
    }
    saving.value = true
    error.value = null
    try {
      const saved = await api.updateFloorplan(projectId.value, floorplan.value)
      floorplan.value = saved as FloorPlanData
    } catch (e) {
      error.value = e instanceof Error ? e.message : '保存失败'
    } finally {
      saving.value = false
    }
  }

  function selectRoom(roomId: string) {
    selectedRoomId.value = roomId
  }

  function updateRoomName(name: string) {
    if (!floorplan.value || !selectedRoom.value) {
      return
    }
    floorplan.value.rooms = floorplan.value.rooms.map((room) =>
      room.id === selectedRoom.value?.id ? { ...room, name } : room,
    )
  }

  function roomLabel(room: FloorRoom) {
    const area = room.area != null ? ` ${room.area}㎡` : ''
    return `${room.name}${area}`
  }

  function roomCenter(room: FloorRoom) {
    return polygonCentroid(room.polygon)
  }

  async function confirmFloorplan() {
    if (!floorplan.value) {
      return
    }
    saving.value = true
    error.value = null
    try {
      const payload = { ...floorplan.value, status: 'confirmed' }
      await api.updateFloorplan(projectId.value, payload)
      router.push({ name: 'design-studio', params: { id: projectId.value } })
    } catch (e) {
      error.value = e instanceof Error ? e.message : '确认失败'
    } finally {
      saving.value = false
    }
  }

  return {
    floorplan,
    selectedRoomId,
    selectedRoom,
    viewBox,
    scaleText,
    loading,
    saving,
    error,
    load,
    save,
    selectRoom,
    updateRoomName,
    roomLabel,
    roomCenter,
    confirmFloorplan,
  }
}
