import { computed, ref } from 'vue'
import type { Ref } from 'vue'
import { useRouter } from 'vue-router'

import { snapPointToWalls } from '@/utils/geometry'
import { api } from '@/api/client'
import { DEFAULT_ROOM_TYPE, type RoomTypeKey } from '@/constants/roomTypes'
import { useManualRoom } from '@/components/FloorPlanEditor/useManualRoom'
import {
  computeViewBox,
  polygonCentroid,
  scaleLabel,
  type FloorPlanData,
  type FloorPoint,
  type FloorRoom,
} from '@/types/floorplan'

export type EditorMode = 'select' | 'scale'

export function useFloorPlanCanvas(projectId: Ref<number>) {
  const router = useRouter()
  const floorplan = ref<FloorPlanData | null>(null)
  const selectedRoomId = ref<string | null>(null)
  const editorMode = ref<EditorMode>('select')
  const scalePoints = ref<[FloorPoint | null, FloorPoint | null]>([null, null])
  const scaleDistanceM = ref('')
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const placementMode = ref<{ active: true; typeKey: RoomTypeKey } | null>(null)
  const { addRoomAt, removeRoom } = useManualRoom(floorplan)

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

  const validationLevel = computed(() => floorplan.value?.validation?.level ?? 'unknown')

  const validationIssues = computed(
    () => floorplan.value?.validation?.issues?.filter((issue) => issue.severity !== 'info') ?? [],
  )

  const hasValidationError = computed(() => validationLevel.value === 'error')

  const canConfirm = computed(
    () =>
      Boolean(floorplan.value?.rooms.length)
      && !hasValidationError.value
      && !saving.value
      && !placementMode.value?.active,
  )

  const canDeleteRoom = computed(
    () => Boolean(selectedRoomId.value) && (floorplan.value?.rooms.length ?? 0) > 1 && !placementMode.value?.active,
  )

  const isPlacementActive = computed(() => Boolean(placementMode.value?.active))

  const scaleMarkers = computed(() => scalePoints.value.filter((point): point is FloorPoint => point != null))

  const canApplyScale = computed(() => {
    const distance = Number(scaleDistanceM.value)
    return scalePoints.value[0] != null && scalePoints.value[1] != null && Number.isFinite(distance) && distance > 0
  })

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
    if (editorMode.value !== 'select' || placementMode.value?.active) {
      return
    }
    selectedRoomId.value = roomId
  }

  function startPlacement(typeKey: RoomTypeKey = DEFAULT_ROOM_TYPE) {
    if (editorMode.value !== 'select') {
      editorMode.value = 'select'
      resetScalePoints()
    }
    placementMode.value = { active: true, typeKey }
  }

  function cancelPlacement() {
    placementMode.value = null
  }

  function placeAt(point: FloorPoint) {
    if (!placementMode.value?.active) {
      return
    }
    const typeKey = placementMode.value.typeKey
    const roomId = addRoomAt(typeKey, point)
    placementMode.value = null
    if (roomId) {
      selectedRoomId.value = roomId
    }
  }

  function deleteSelectedRoom(): boolean {
    if (!selectedRoomId.value || !canDeleteRoom.value) {
      return false
    }
    const roomId = selectedRoomId.value
    const roomName = selectedRoom.value?.name ?? roomId
    const proceed = window.confirm(`确定删除「${roomName}」？`)
    if (!proceed) {
      return false
    }
    if (!removeRoom(roomId)) {
      return false
    }
    selectedRoomId.value = floorplan.value?.rooms[0]?.id ?? null
    return true
  }

  function setEditorMode(mode: EditorMode) {
    editorMode.value = mode
    if (mode === 'select') {
      resetScalePoints()
    } else {
      cancelPlacement()
    }
  }

  function resetScalePoints() {
    scalePoints.value = [null, null]
  }

  function addScalePoint(point: FloorPoint) {
    if (editorMode.value !== 'scale') {
      return
    }
    if (!scalePoints.value[0]) {
      scalePoints.value = [point, scalePoints.value[1]]
      return
    }
    if (!scalePoints.value[1]) {
      scalePoints.value = [scalePoints.value[0], point]
      return
    }
    scalePoints.value = [point, null]
  }

  async function applyScale() {
    const pointA = scalePoints.value[0]
    const pointB = scalePoints.value[1]
    const distance = Number(scaleDistanceM.value)
    if (!pointA || !pointB || !Number.isFinite(distance) || distance <= 0) {
      return
    }
    saving.value = true
    error.value = null
    try {
      const saved = await api.setFloorplanScale(projectId.value, pointA, pointB, distance)
      floorplan.value = saved as FloorPlanData
      resetScalePoints()
      editorMode.value = 'select'
    } catch (e) {
      error.value = e instanceof Error ? e.message : '比例尺标定失败'
    } finally {
      saving.value = false
    }
  }

  function updateRoomName(name: string) {
    if (!floorplan.value || !selectedRoom.value) {
      return
    }
    floorplan.value.rooms = floorplan.value.rooms.map((room) =>
      room.id === selectedRoom.value?.id ? { ...room, name } : room,
    )
  }

  function updateRoomVertex(roomId: string, vertexIndex: number, point: FloorPoint) {
    if (!floorplan.value) {
      return
    }
    const snapped = snapPointToWalls(point, floorplan.value.walls)
    floorplan.value.rooms = floorplan.value.rooms.map((room) => {
      if (room.id !== roomId) {
        return room
      }
      const polygon = room.polygon.map((vertex, index) =>
        index === vertexIndex ? { ...snapped } : vertex,
      )
      return { ...room, polygon }
    })
  }

  function roomLabel(room: FloorRoom) {
    const area = room.area != null ? ` ${room.area}㎡` : ''
    return `${room.name}${area}`
  }

  function roomCenter(room: FloorRoom) {
    return polygonCentroid(room.polygon)
  }

  async function confirmFloorplan() {
    if (!floorplan.value || hasValidationError.value) {
      return
    }
    if (validationLevel.value === 'warning') {
      const proceed = window.confirm('户型质检存在警告项，确认仍要继续进入设计吗？')
      if (!proceed) {
        return
      }
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
    editorMode,
    placementMode,
    isPlacementActive,
    scalePoints,
    scaleDistanceM,
    scaleMarkers,
    canApplyScale,
    viewBox,
    scaleText,
    loading,
    saving,
    error: error,
    load,
    save,
    selectRoom,
    startPlacement,
    cancelPlacement,
    placeAt,
    deleteSelectedRoom,
    canDeleteRoom,
    setEditorMode,
    addScalePoint,
    resetScalePoints,
    applyScale,
    updateRoomName,
    updateRoomVertex,
    roomLabel,
    roomCenter,
    confirmFloorplan,
    validationLevel,
    validationIssues,
    hasValidationError,
    canConfirm,
  }
}
