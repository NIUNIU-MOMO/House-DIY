<script setup lang="ts">
import { computed, ref } from 'vue'

import {
  computeViewBox,
  polygonCentroid,
  svgPointFromEvent,
  type FloorPlanData,
  type FloorPoint,
  type FloorRoom,
} from '@/types/floorplan'
import type { SnapKind } from '@/utils/geometry'

import type { EditorMode } from './useCanvas'

const props = withDefaults(
  defineProps<{
    floorplan: FloorPlanData
    selectedRoomId?: string | null
    selectedVertexIndex?: number | null
    showUnderlay?: boolean
    underlayOpacity?: number
    labelScale?: number
    editable?: boolean
    editorMode?: EditorMode
    scaleMarkers?: FloorPoint[]
    placementActive?: boolean
    traceActive?: boolean
    tracePoints?: FloorPoint[]
    snapPreview?: { point: FloorPoint; kind: SnapKind } | null
  }>(),
  {
    selectedRoomId: null,
    selectedVertexIndex: null,
    showUnderlay: true,
    underlayOpacity: 0.35,
    labelScale: 1,
    editable: false,
    editorMode: 'select',
    scaleMarkers: () => [],
    placementActive: false,
    traceActive: false,
    tracePoints: () => [],
    snapPreview: null,
  },
)

const emit = defineEmits<{
  canvasClick: [point: FloorPoint]
  backgroundClick: []
  roomSelect: [roomId: string]
  vertexMove: [payload: { roomId: string; vertexIndex: number; point: FloorPoint }]
  vertexSelect: [vertexIndex: number]
  vertexDelete: [vertexIndex: number]
  edgeMove: [payload: { roomId: string; edgeIndex: number; delta: FloorPoint }]
  edgeInsertVertex: [edgeIndex: number]
  contextMenu: [payload: { point: FloorPoint; clientX: number; clientY: number }]
  traceClick: [point: FloorPoint]
  traceClose: []
  traceMove: [point: FloorPoint]
}>()

const svgRef = ref<SVGSVGElement | null>(null)
const dragging = ref<{ roomId: string; vertexIndex: number } | null>(null)
const edgeDragging = ref<{ roomId: string; edgeIndex: number; last: FloorPoint } | null>(null)

const CLOSE_TRACE_DISTANCE = 12

const viewBox = computed(() => computeViewBox(props.floorplan))
const wallStroke = computed(() => (props.floorplan.walls.length ? 3 : 2))
const fontSize = computed(() => 12 * props.labelScale)
const subFontSize = computed(() => 10 * props.labelScale)

const selectedRoom = computed(() =>
  props.floorplan.rooms.find((room) => room.id === props.selectedRoomId) ?? null,
)

const scaleLine = computed(() => {
  if (props.scaleMarkers.length !== 2) {
    return null
  }
  const start = props.scaleMarkers[0]
  const end = props.scaleMarkers[1]
  if (!start || !end) {
    return null
  }
  return { start, end }
})

function roomCenter(room: FloorRoom) {
  return polygonCentroid(room.polygon)
}

function isSelected(roomId: string) {
  return props.selectedRoomId === roomId
}

function roomFill(roomId: string) {
  return isSelected(roomId) ? 'rgba(201, 125, 58, 0.42)' : 'rgba(44, 74, 62, 0.24)'
}

function roomStroke(roomId: string) {
  return isSelected(roomId) ? '#c97d3a' : '#2c4a3e'
}

function roomStrokeWidth(roomId: string) {
  return isSelected(roomId) ? 3 : 1.5
}

function edgeMidpoint(a: FloorPoint, b: FloorPoint) {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }
}

function distance(a: FloorPoint, b: FloorPoint) {
  return Math.hypot(a.x - b.x, a.y - b.y)
}

function canCloseOnPoint(point: FloorPoint) {
  const first = props.tracePoints[0]
  if (!first || props.tracePoints.length < 3) {
    return false
  }
  return distance(first, point) <= CLOSE_TRACE_DISTANCE
}

function onSvgClick(event: MouseEvent) {
  if (!svgRef.value || dragging.value || edgeDragging.value) {
    return
  }
  if (!props.editable) {
    emit('backgroundClick')
    return
  }
  const point = svgPointFromEvent(event, svgRef.value)
  if (props.traceActive) {
    if (canCloseOnPoint(point)) {
      emit('traceClose')
      return
    }
    emit('traceClick', point)
    return
  }
  if (props.placementActive) {
    emit('canvasClick', point)
    return
  }
  if (props.editorMode === 'scale') {
    emit('canvasClick', point)
    return
  }
  if (props.editorMode === 'select') {
    emit('backgroundClick')
  }
}

function onSvgMouseMove(event: MouseEvent) {
  if (!props.editable || !svgRef.value || !props.traceActive) {
    return
  }
  emit('traceMove', svgPointFromEvent(event, svgRef.value))
}

function onRoomClick(event: MouseEvent, roomId: string) {
  if (props.traceActive) {
    return
  }
  if (!props.editable) {
    event.stopPropagation()
    emit('roomSelect', roomId)
    return
  }
  if (props.editorMode !== 'select') {
    return
  }
  event.stopPropagation()
  emit('roomSelect', roomId)
}

function onVertexPointerDown(
  event: PointerEvent,
  roomId: string,
  vertexIndex: number,
) {
  if (!props.editable || props.editorMode !== 'select' || props.traceActive) {
    return
  }
  event.stopPropagation()
  emit('vertexSelect', vertexIndex)
  dragging.value = { roomId, vertexIndex }
  ;(event.target as Element).setPointerCapture(event.pointerId)
}

function onVertexPointerMove(event: PointerEvent) {
  if (!dragging.value || !svgRef.value) {
    return
  }
  const point = svgPointFromEvent(event, svgRef.value)
  emit('vertexMove', {
    roomId: dragging.value.roomId,
    vertexIndex: dragging.value.vertexIndex,
    point,
  })
}

function onSvgContextMenu(event: MouseEvent) {
  if (!props.editable || !svgRef.value || props.editorMode !== 'select' || props.placementActive || props.traceActive) {
    return
  }
  event.preventDefault()
  const point = svgPointFromEvent(event, svgRef.value)
  emit('contextMenu', { point, clientX: event.clientX, clientY: event.clientY })
}

function onVertexContextMenu(event: MouseEvent, vertexIndex: number) {
  if (!props.editable || props.editorMode !== 'select' || props.traceActive) {
    return
  }
  event.preventDefault()
  event.stopPropagation()
  emit('vertexDelete', vertexIndex)
}

function onEdgePointerDown(event: PointerEvent, roomId: string, edgeIndex: number) {
  if (!props.editable || props.editorMode !== 'select' || !svgRef.value || props.traceActive) {
    return
  }
  event.stopPropagation()
  edgeDragging.value = {
    roomId,
    edgeIndex,
    last: svgPointFromEvent(event, svgRef.value),
  }
  ;(event.target as Element).setPointerCapture(event.pointerId)
}

function onEdgeDoubleClick(event: MouseEvent, edgeIndex: number) {
  if (!props.editable || props.editorMode !== 'select' || props.traceActive) {
    return
  }
  event.stopPropagation()
  emit('edgeInsertVertex', edgeIndex)
}

function onEdgePointerMove(event: PointerEvent) {
  if (!edgeDragging.value || !svgRef.value) {
    return
  }
  const current = svgPointFromEvent(event, svgRef.value)
  const delta = {
    x: current.x - edgeDragging.value.last.x,
    y: current.y - edgeDragging.value.last.y,
  }
  edgeDragging.value.last = current
  emit('edgeMove', {
    roomId: edgeDragging.value.roomId,
    edgeIndex: edgeDragging.value.edgeIndex,
    delta,
  })
}

function onVertexPointerUp(event: PointerEvent) {
  if (!dragging.value) {
    return
  }
  ;(event.target as Element).releasePointerCapture(event.pointerId)
  dragging.value = null
}

function onEdgePointerUp(event: PointerEvent) {
  if (!edgeDragging.value) {
    return
  }
  ;(event.target as Element).releasePointerCapture(event.pointerId)
  edgeDragging.value = null
}
</script>

<template>
  <svg
    ref="svgRef"
    :viewBox="viewBox"
    class="floor-svg"
    :class="{
      interactive: editable,
      'mode-scale': editable && editorMode === 'scale',
      'placement-active': editable && placementActive,
      'trace-active': editable && traceActive,
    }"
    @click="onSvgClick"
    @mousemove="onSvgMouseMove"
    @contextmenu="onSvgContextMenu"
  >
    <rect
      v-if="!showUnderlay || !floorplan.source_url"
      x="0"
      y="0"
      :width="floorplan.source_width ?? 800"
      :height="floorplan.source_height ?? 600"
      fill="#f8f4ee"
    />
    <image
      v-if="showUnderlay && floorplan.source_url && floorplan.source_width && floorplan.source_height"
      :href="floorplan.source_url"
      x="0"
      y="0"
      :width="floorplan.source_width"
      :height="floorplan.source_height"
      class="floor-underlay"
      :style="{ opacity: underlayOpacity }"
      preserveAspectRatio="none"
    />
    <g v-for="room in floorplan.rooms" :key="room.id">
      <polygon
        :points="room.polygon.map((p) => `${p.x},${p.y}`).join(' ')"
        :fill="roomFill(room.id)"
        :stroke="roomStroke(room.id)"
        :stroke-width="roomStrokeWidth(room.id)"
        :class="{ 'room-hit': (!editable || (editorMode === 'select' && !traceActive)) }"
        @click="onRoomClick($event, room.id)"
      />
    </g>
    <g v-for="wall in floorplan.walls" :key="wall.id">
      <polyline
        :points="wall.points.map((p) => `${p.x},${p.y}`).join(' ')"
        fill="none"
        stroke="#1a2f28"
        :stroke-width="wallStroke"
      />
    </g>

    <g v-if="traceActive && tracePoints.length" class="trace-overlay">
      <polyline
        v-if="tracePoints.length > 1"
        :points="tracePoints.map((p) => `${p.x},${p.y}`).join(' ')"
        class="trace-line"
      />
      <circle
        v-for="(point, index) in tracePoints"
        :key="`trace-${index}`"
        :cx="point.x"
        :cy="point.y"
        :r="index === 0 && tracePoints.length >= 3 ? 9 : 6"
        class="trace-point"
        :class="{ 'trace-point-close': index === 0 && tracePoints.length >= 3 }"
      />
      <text
        v-for="(point, index) in tracePoints"
        :key="`trace-label-${index}`"
        :x="point.x + 10"
        :y="point.y - 8"
        class="trace-point-label"
      >
        {{ index + 1 }}
      </text>
    </g>

    <g v-if="snapPreview" class="snap-preview">
      <circle
        :cx="snapPreview.point.x"
        :cy="snapPreview.point.y"
        r="7"
        :class="snapPreview.kind === 'corner' ? 'snap-corner' : 'snap-segment'"
      />
    </g>

    <g
      v-if="editable && editorMode === 'select' && selectedRoom && !traceActive"
      class="vertex-handles"
    >
      <circle
        v-for="(vertex, index) in selectedRoom.polygon"
        :key="`${selectedRoom.id}-v-${index}`"
        :cx="vertex.x"
        :cy="vertex.y"
        r="6"
        class="vertex-handle"
        :class="{ 'vertex-handle-selected': selectedVertexIndex === index }"
        @click.stop
        @contextmenu="onVertexContextMenu($event, index)"
        @pointerdown="onVertexPointerDown($event, selectedRoom.id, index)"
        @pointermove="onVertexPointerMove"
        @pointerup="onVertexPointerUp"
        @pointercancel="onVertexPointerUp"
      />
      <circle
        v-for="(vertex, index) in selectedRoom.polygon"
        :key="`${selectedRoom.id}-e-${index}`"
        :cx="edgeMidpoint(vertex, selectedRoom.polygon[(index + 1) % selectedRoom.polygon.length]).x"
        :cy="edgeMidpoint(vertex, selectedRoom.polygon[(index + 1) % selectedRoom.polygon.length]).y"
        r="5"
        class="edge-handle"
        :data-testid="`edge-handle-${index}`"
        @click.stop
        @dblclick="onEdgeDoubleClick($event, index)"
        @pointerdown="onEdgePointerDown($event, selectedRoom.id, index)"
        @pointermove="onEdgePointerMove"
        @pointerup="onEdgePointerUp"
        @pointercancel="onEdgePointerUp"
      />
    </g>
    <g v-if="scaleMarkers.length" class="scale-markers">
      <circle
        v-for="(marker, index) in scaleMarkers"
        :key="`scale-${index}`"
        :cx="marker.x"
        :cy="marker.y"
        r="7"
        class="scale-marker"
      />
      <text
        v-for="(marker, index) in scaleMarkers"
        :key="`scale-label-${index}`"
        :x="marker.x + 10"
        :y="marker.y - 10"
        class="scale-marker-label"
      >
        {{ index === 0 ? 'A' : 'B' }}
      </text>
      <line
        v-if="scaleLine"
        :x1="scaleLine.start.x"
        :y1="scaleLine.start.y"
        :x2="scaleLine.end.x"
        :y2="scaleLine.end.y"
        class="scale-marker-line"
      />
    </g>
    <g v-for="room in floorplan.rooms" :key="`${room.id}-label`">
      <text
        class="room-label"
        :x="roomCenter(room).x"
        :y="roomCenter(room).y"
        text-anchor="middle"
        dominant-baseline="middle"
        :font-size="fontSize"
        pointer-events="none"
      >
        <tspan :x="roomCenter(room).x" dy="-0.4em">{{ room.name }}</tspan>
        <tspan
          v-if="room.area != null"
          :x="roomCenter(room).x"
          dy="1.3em"
          :font-size="subFontSize"
          class="room-area"
        >
          {{ room.area }}㎡
        </tspan>
      </text>
    </g>
  </svg>
</template>

<style scoped>
.floor-svg {
  width: 100%;
  max-width: 900px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
  background: #fff;
}

.floor-svg.interactive.mode-scale,
.floor-svg.interactive.placement-active,
.floor-svg.interactive.trace-active {
  cursor: crosshair;
}

.floor-underlay {
  pointer-events: none;
}

.room-hit {
  cursor: pointer;
}

.edge-handle {
  fill: #2c4a3e;
  stroke: #fff;
  stroke-width: 2;
  cursor: move;
}

.vertex-handle {
  fill: #fff;
  stroke: #c97d3a;
  stroke-width: 2;
  cursor: grab;
}

.vertex-handle-selected {
  fill: #c97d3a;
  stroke: #1a2f28;
}

.vertex-handle:active {
  cursor: grabbing;
}

.trace-line {
  fill: none;
  stroke: #c97d3a;
  stroke-width: 2;
  stroke-dasharray: 6 4;
  pointer-events: none;
}

.trace-point {
  fill: rgba(201, 125, 58, 0.9);
  stroke: #fff;
  stroke-width: 2;
  pointer-events: none;
}

.trace-point-close {
  fill: rgba(44, 74, 62, 0.85);
}

.trace-point-label {
  fill: #c97d3a;
  font-size: 11px;
  font-weight: 700;
  font-family: var(--sans);
  pointer-events: none;
}

.snap-corner {
  fill: rgba(60, 140, 80, 0.35);
  stroke: #3c8c50;
  stroke-width: 2;
  pointer-events: none;
}

.snap-segment {
  fill: rgba(120, 120, 120, 0.25);
  stroke: #666;
  stroke-width: 2;
  pointer-events: none;
}

.scale-marker {
  fill: rgba(201, 125, 58, 0.85);
  stroke: #fff;
  stroke-width: 2;
}

.scale-marker-label {
  fill: #c97d3a;
  font-size: 12px;
  font-weight: 700;
  font-family: var(--sans);
}

.scale-marker-line {
  stroke: #c97d3a;
  stroke-width: 2;
  stroke-dasharray: 6 4;
  pointer-events: none;
}

.room-label {
  fill: #1a2f28;
  font-family: var(--sans);
  font-weight: 600;
  paint-order: stroke fill;
  stroke: rgba(255, 255, 255, 0.92);
  stroke-width: 4px;
  stroke-linejoin: round;
}

.room-area {
  fill: #4a5c54;
  font-weight: 500;
}
</style>
