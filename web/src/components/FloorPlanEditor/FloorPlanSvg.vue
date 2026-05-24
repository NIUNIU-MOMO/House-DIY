<script setup lang="ts">
import { computed } from 'vue'

import {
  computeViewBox,
  polygonCentroid,
  type FloorPlanData,
  type FloorRoom,
} from '@/types/floorplan'

const props = withDefaults(
  defineProps<{
    floorplan: FloorPlanData
    selectedRoomId?: string | null
    showUnderlay?: boolean
    underlayOpacity?: number
    labelScale?: number
  }>(),
  {
    selectedRoomId: null,
    showUnderlay: true,
    underlayOpacity: 0.35,
    labelScale: 1,
  },
)

const viewBox = computed(() => computeViewBox(props.floorplan))
const wallStroke = computed(() => (props.floorplan.walls.length ? 3 : 2))
const fontSize = computed(() => 12 * props.labelScale)
const subFontSize = computed(() => 10 * props.labelScale)

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
</script>

<template>
  <svg :viewBox="viewBox" class="floor-svg">
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
    <g v-for="room in floorplan.rooms" :key="`${room.id}-label`">
      <text
        class="room-label"
        :x="roomCenter(room).x"
        :y="roomCenter(room).y"
        text-anchor="middle"
        dominant-baseline="middle"
        :font-size="fontSize"
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

.floor-underlay {
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
