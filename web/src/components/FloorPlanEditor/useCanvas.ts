import { computed, ref } from 'vue'
import type { Ref } from 'vue'
import { useRouter } from 'vue-router'

import { snapAnnotationPoint } from '@/utils/geometry'
import { api } from '@/api/client'
import { DEFAULT_ROOM_TYPE, type RoomTypeKey } from '@/constants/roomTypes'
import { useManualRoom } from '@/components/FloorPlanEditor/useManualRoom'
import { cloneFloorplanSnapshot } from '@/components/FloorPlanEditor/floorplanSnapshot'
import {
  applyPolygonToRoom,
  insertVertexOnEdge,
  removeVertexFromPolygon,
  updateRoomPolygon,
} from '@/components/FloorPlanEditor/usePolygonEdit'
import { useTraceMode } from '@/components/FloorPlanEditor/useTraceMode'
import {
  computeViewBox,
  polygonCentroid,
  scaleLabel,
  type FloorPlanData,
  type FloorPoint,
  type FloorRoom,
} from '@/types/floorplan'

export type EditorMode = 'select' | 'scale'
export type AnnotationSubMode = 'adjust' | 'trace' | 'place-rect'

export function useFloorPlanCanvas(projectId: Ref<number>) {
  const router = useRouter()
  const floorplan = ref<FloorPlanData | null>(null)
  const selectedRoomId = ref<string | null>(null)
  const selectedVertexIndex = ref<number | null>(null)
  const editorMode = ref<EditorMode>('select')
  const annotationSubMode = ref<AnnotationSubMode>('adjust')
  const cornerSnapEnabled = ref(true)
  const scalePoints = ref<[FloorPoint | null, FloorPoint | null]>([null, null])
  const scaleDistanceM = ref('')
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const isDirty = ref(false)
  const placementMode = ref<{ active: true; typeKey: RoomTypeKey } | null>(null)
  const { addRoomAt, removeRoom } = useManualRoom(floorplan)
  const trace = useTraceMode()

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

  const isTraceActive = computed(() => trace.isTraceActive.value)

  const canConfirm = computed(
    () =>
      Boolean(floorplan.value?.rooms.length)
      && !hasValidationError.value
      && !saving.value
      && !placementMode.value?.active
      && !trace.isTraceActive.value,
  )

  const canDeleteRoom = computed(
    () =>
      Boolean(selectedRoomId.value)
      && (floorplan.value?.rooms.length ?? 0) > 1
      && !placementMode.value?.active
      && !trace.isTraceActive.value,
  )

  const isPlacementActive = computed(() => Boolean(placementMode.value?.active))

  const scaleMarkers = computed(() => scalePoints.value.filter((point): point is FloorPoint => point != null))

  const canApplyScale = computed(() => {
    const distance = Number(scaleDistanceM.value)
    return scalePoints.value[0] != null && scalePoints.value[1] != null && Number.isFinite(distance) && distance > 0
  })

  function snapOptions(skipSnap = false) {
    return {
      cornerSnapEnabled: cornerSnapEnabled.value,
      skipSnap,
    }
  }

  function exitAnnotationModes() {
    placementMode.value = null
    trace.cancelTrace()
    annotationSubMode.value = 'adjust'
  }

  async function load() {
    loading.value = true
    error.value = null
    try {
      const data = (await api.getFloorplan(projectId.value)) as FloorPlanData
      floorplan.value = data
      selectedRoomId.value = data.rooms[0]?.id ?? null
      selectedVertexIndex.value = null
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  function markDirty() {
    isDirty.value = true
  }

  async function save() {
    if (!floorplan.value) {
      return false
    }
    saving.value = true
    error.value = null
    try {
      const payload = { ...floorplan.value, status: 'draft' }
      const saved = await api.saveFloorplanAnnotation(projectId.value, payload)
      floorplan.value = saved as FloorPlanData
      isDirty.value = false
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : '保存失败'
      return false
    } finally {
      saving.value = false
    }
  }

  function selectRoom(roomId: string) {
    if (editorMode.value !== 'select' || placementMode.value?.active || trace.isTraceActive.value) {
      return
    }
    selectedRoomId.value = roomId
    selectedVertexIndex.value = null
    annotationSubMode.value = 'adjust'
  }

  function selectVertex(vertexIndex: number) {
    selectedVertexIndex.value = vertexIndex
  }

  function startPlacement(typeKey: RoomTypeKey = DEFAULT_ROOM_TYPE) {
    if (editorMode.value !== 'select') {
      editorMode.value = 'select'
      resetScalePoints()
    }
    trace.cancelTrace()
    placementMode.value = { active: true, typeKey }
    annotationSubMode.value = 'place-rect'
  }

  function cancelPlacement() {
    placementMode.value = null
    annotationSubMode.value = 'adjust'
  }

  function startTrace(typeKey: RoomTypeKey = DEFAULT_ROOM_TYPE, redrawRoomId: string | null = null) {
    if (editorMode.value !== 'select') {
      editorMode.value = 'select'
      resetScalePoints()
    }
    placementMode.value = null
    trace.startTrace(typeKey, redrawRoomId)
    annotationSubMode.value = 'trace'
    error.value = null
  }

  function cancelTrace() {
    trace.cancelTrace()
    annotationSubMode.value = 'adjust'
  }

  function undoTracePoint() {
    trace.undoTracePoint()
  }

  function addTracePoint(point: FloorPoint, skipSnap = false) {
    if (!floorplan.value || !trace.isTraceActive.value) {
      return false
    }
    return trace.addTracePoint(point, floorplan.value.walls, snapOptions(skipSnap))
  }

  function finishTrace(): boolean {
    if (!floorplan.value || !trace.isTraceActive.value) {
      return false
    }
    const polygon = trace.closeTrace()
    if (!polygon) {
      error.value = trace.traceError.value
      return false
    }
    const room = trace.buildTraceRoom(polygon, floorplan.value.rooms, floorplan.value.scale)
    if (!room) {
      return false
    }
    if (trace.traceTarget.value?.redrawRoomId) {
      floorplan.value = {
        ...floorplan.value,
        rooms: updateRoomPolygon(floorplan.value.rooms, room.id, room.polygon, floorplan.value.scale),
      }
    } else {
      floorplan.value = {
        ...floorplan.value,
        rooms: [...floorplan.value.rooms, room],
      }
    }
    selectedRoomId.value = room.id
    selectedVertexIndex.value = null
    trace.cancelTrace()
    annotationSubMode.value = 'adjust'
    error.value = null
    markDirty()
    return true
  }

  function startRetraceSelectedRoom() {
    if (!selectedRoom.value) {
      return
    }
    startTrace(DEFAULT_ROOM_TYPE, selectedRoom.value.id)
  }

  function placeAt(point: FloorPoint) {
    if (!placementMode.value?.active) {
      return
    }
    const typeKey = placementMode.value.typeKey
    const roomId = addRoomAt(typeKey, point)
    placementMode.value = null
    annotationSubMode.value = 'adjust'
    if (roomId) {
      selectedRoomId.value = roomId
    }
    markDirty()
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
    selectedVertexIndex.value = null
    markDirty()
    return true
  }

  function setEditorMode(mode: EditorMode) {
    editorMode.value = mode
    if (mode === 'select') {
      resetScalePoints()
    } else {
      exitAnnotationModes()
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
    markDirty()
  }

  function updateRoomVertex(roomId: string, vertexIndex: number, point: FloorPoint) {
    if (!floorplan.value) {
      return
    }
    const room = floorplan.value.rooms.find((item) => item.id === roomId)
    if (!room) {
      return
    }
    const snapped = snapAnnotationPoint(point, floorplan.value.walls, snapOptions()).point
    const polygon = room.polygon.map((vertex, index) =>
      index === vertexIndex ? { ...snapped } : vertex,
    )
    floorplan.value = {
      ...floorplan.value,
      rooms: updateRoomPolygon(floorplan.value.rooms, roomId, polygon, floorplan.value.scale),
    }
    markDirty()
  }

  function insertVertexOnSelectedEdge(edgeIndex: number) {
    if (!floorplan.value || !selectedRoomId.value) {
      return false
    }
    const room = floorplan.value.rooms.find((item) => item.id === selectedRoomId.value)
    if (!room) {
      return false
    }
    const nextPolygon = insertVertexOnEdge(room.polygon, edgeIndex, floorplan.value.walls, snapOptions())
    if (!nextPolygon) {
      return false
    }
    floorplan.value = {
      ...floorplan.value,
      rooms: updateRoomPolygon(floorplan.value.rooms, room.id, nextPolygon, floorplan.value.scale),
    }
    selectedVertexIndex.value = edgeIndex + 1
    markDirty()
    return true
  }

  function removeSelectedVertex(vertexIndex?: number) {
    if (!floorplan.value || !selectedRoomId.value) {
      return false
    }
    const room = floorplan.value.rooms.find((item) => item.id === selectedRoomId.value)
    if (!room) {
      return false
    }
    const targetIndex = vertexIndex ?? selectedVertexIndex.value
    if (targetIndex == null) {
      return false
    }
    const nextPolygon = removeVertexFromPolygon(room.polygon, targetIndex)
    if (!nextPolygon) {
      error.value = '至少保留 3 个顶点'
      return false
    }
    floorplan.value = {
      ...floorplan.value,
      rooms: updateRoomPolygon(floorplan.value.rooms, room.id, nextPolygon, floorplan.value.scale),
    }
    selectedVertexIndex.value = null
    error.value = null
    markDirty()
    return true
  }

  function moveRoomEdge(roomId: string, edgeIndex: number, delta: FloorPoint) {
    if (!floorplan.value) {
      return
    }
    floorplan.value.rooms = floorplan.value.rooms.map((room) => {
      if (room.id !== roomId) {
        return room
      }
      const nextIndex = (edgeIndex + 1) % room.polygon.length
      const polygon = room.polygon.map((vertex, index) => {
        if (index === edgeIndex || index === nextIndex) {
          return { x: vertex.x + delta.x, y: vertex.y + delta.y }
        }
        return vertex
      })
      return applyPolygonToRoom(room, polygon, floorplan.value!.scale)
    })
    markDirty()
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
    if (isDirty.value) {
      const saved = await save()
      if (!saved) {
        return
      }
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
      await api.confirmFloorplan(projectId.value)
      isDirty.value = false
      router.push({ name: 'design-studio', params: { id: projectId.value } })
    } catch (e) {
      error.value = e instanceof Error ? e.message : '确认失败'
    } finally {
      saving.value = false
    }
  }

  function addRoomAtPoint(typeKey: RoomTypeKey, point: FloorPoint) {
    startPlacement(typeKey)
    placeAt(point)
  }

  function snapshotFloorplan(): FloorPlanData | null {
    if (!floorplan.value) {
      return null
    }
    return cloneFloorplanSnapshot(floorplan.value)
  }

  function restoreFloorplanSnapshot(data: FloorPlanData) {
    floorplan.value = cloneFloorplanSnapshot(data)
    selectedRoomId.value = data.rooms[0]?.id ?? null
    selectedVertexIndex.value = null
    exitAnnotationModes()
    resetScalePoints()
    editorMode.value = 'select'
  }

  function previewSnap(point: FloorPoint, skipSnap = false) {
    if (!floorplan.value) {
      return { point, kind: 'none' as const }
    }
    return snapAnnotationPoint(point, floorplan.value.walls, snapOptions(skipSnap))
  }

  return {
    floorplan,
    selectedRoomId,
    selectedRoom,
    selectedVertexIndex,
    editorMode,
    annotationSubMode,
    cornerSnapEnabled,
    placementMode,
    isPlacementActive,
    isTraceActive,
    tracePoints: trace.tracePoints,
    traceError: trace.traceError,
    canCloseTrace: trace.canCloseTrace,
    scalePoints,
    scaleDistanceM,
    scaleMarkers,
    canApplyScale,
    viewBox,
    scaleText,
    loading,
    saving,
    error: error,
    isDirty,
    markDirty,
    load,
    save,
    selectRoom,
    selectVertex,
    startPlacement,
    cancelPlacement,
    startTrace,
    cancelTrace,
    undoTracePoint,
    addTracePoint,
    finishTrace,
    startRetraceSelectedRoom,
    placeAt,
    addRoomAtPoint,
    deleteSelectedRoom,
    canDeleteRoom,
    setEditorMode,
    addScalePoint,
    resetScalePoints,
    applyScale,
    updateRoomName,
    updateRoomVertex,
    insertVertexOnSelectedEdge,
    removeSelectedVertex,
    moveRoomEdge,
    roomLabel,
    roomCenter,
    confirmFloorplan,
    validationLevel,
    validationIssues,
    hasValidationError,
    canConfirm,
    snapshotFloorplan,
    restoreFloorplanSnapshot,
    previewSnap,
  }
}
