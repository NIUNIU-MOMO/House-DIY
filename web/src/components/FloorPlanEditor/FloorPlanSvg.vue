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

import type { EditorMode } from './useCanvas'

const props = withDefaults(
  defineProps<{
    floorplan: FloorPlanData
    selectedRoomId?: string | null
    showUnderlay?: boolean
    underlayOpacity?: number
    labelScale?: number
    editable?: boolean
    editorMode?: EditorMode
    scaleMarkers?: FloorPoint[]
  }>(),
  {
    selectedRoomId: null,
    showUnderlay: true,
    underlayOpacity: 0.35,
    labelScale: 1,
    editable: false,
    editorMode: 'select',
    scaleMarkers: () => [],
  },
)

const emit = defineEmits<{
  canvasClick: [point: FloorPoint]
  roomSelect: [roomId: string]
  vertexMove: [payload: { roomId: string; vertexIndex: number; point: FloorPoint }]
}>()

const svgRef = ref<SVGSVGElement | null>(null)
const dragging = ref<{ roomId: string; vertexIndex: number } | null>(null)

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

function onSvgClick(event: MouseEvent) {
  if (!props.editable || !svgRef.value || dragging.value) {
    return
  }
  if (props.editorMode === 'scale') {
    emit('canvasClick', svgPointFromEvent(event, svgRef.value))
  }
}

function onRoomClick(event: MouseEvent, roomId: string) {
  if (!props.editable || props.editorMode !== 'select') {
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
  if (!props.editable || props.editorMode !== 'select') {
    return
  }
  event.stopPropagation()
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

function onVertexPointerUp(event: PointerEvent) {
  if (!dragging.value) {
    return
  }
  ;(event.target as Element).releasePointerCapture(event.pointerId)
  dragging.value = null
}
</script>

<template>
  <svg
    ref="svgRef"
    :viewBox="viewBox"
    class="floor-svg"
    :class="{ interactive: editable, 'mode-scale': editable && editorMode === 'scale' }"
    @click="onSvgClick"
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
        :class="{ 'room-hit': editable && editorMode === 'select' }"
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
    <g
      v-if="editable && editorMode === 'select' && selectedRoom"
      class="vertex-handles"
    >
      <circle
        v-for="(vertex, index) in selectedRoom.polygon"
        :key="`${selectedRoom.id}-v-${index}`"
        :cx="vertex.x"
        :cy="vertex.y"
        r="6"
        class="vertex-handle"
        @pointerdown="onVertexPointerDown($event, selectedRoom.id, index)"
        @pointermove="onVertexPointerMove"
        @pointerup="onVertexPointerUp"
        @pointercancel="onVertexPointerUp"
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

.floor-svg.interactive.mode-scale {
  cursor: crosshair;
}

.floor-underlay {
  pointer-events: none;
}

.room-hit {
  cursor: pointer;
}

.vertex-handle {
  fill: #fff;
  stroke: #c97d3a;
  stroke-width: 2;
  cursor: grab;
}

.vertex-handle:active {
  cursor: grabbing;
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
