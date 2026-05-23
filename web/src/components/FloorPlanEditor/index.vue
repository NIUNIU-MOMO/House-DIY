<script setup lang="ts">
import { computed, onMounted, toRef } from 'vue'

import { useFloorPlanCanvas } from './useCanvas'

const props = defineProps<{
  projectId: number
}>()

const projectId = toRef(props, 'projectId')

const {
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
  goBackToParse,
  goBackToUpload,
} = useFloorPlanCanvas(projectId)

const wallStroke = computed(() => (floorplan.value?.walls.length ? 3 : 2))

onMounted(load)
</script>

<template>
  <div v-if="loading" class="editor-loading">加载户型数据…</div>
  <div v-else-if="error && !floorplan" class="editor-error">{{ error }}</div>
  <div v-else-if="floorplan" class="editor-layout">
    <aside class="editor-tools">
      <h4>工具</h4>
      <button type="button" class="tool active">选择</button>
      <button type="button" class="tool" disabled>墙线</button>
      <button type="button" class="tool" disabled>门洞</button>
      <button type="button" class="tool" disabled>窗户</button>
      <hr />
      <h4>比例尺</h4>
      <p class="tiny muted">{{ scaleText }}</p>
      <hr />
      <h4>房间列表</h4>
      <ul class="room-list">
        <li
          v-for="room in floorplan.rooms"
          :key="room.id"
          :class="{ active: room.id === selectedRoomId }"
          @click="selectRoom(room.id)"
        >
          {{ roomLabel(room) }}
        </li>
      </ul>
    </aside>

    <div class="canvas-area">
      <div class="canvas-toolbar">
        <button type="button" class="btn sm ghost" :disabled="saving" @click="save">
          {{ saving ? '保存中…' : '保存' }}
        </button>
        <span class="muted">状态 · {{ floorplan.status }}</span>
      </div>
      <div class="floor-canvas">
        <svg :viewBox="viewBox" class="floor-svg">
          <image
            v-if="floorplan.source_url && floorplan.source_width && floorplan.source_height"
            :href="floorplan.source_url"
            x="0"
            y="0"
            :width="floorplan.source_width"
            :height="floorplan.source_height"
            class="floor-underlay"
            preserveAspectRatio="none"
          />
          <rect
            v-else
            width="100%"
            height="100%"
            fill="#f8f4ee"
          />
          <g v-for="room in floorplan.rooms" :key="room.id">
            <polygon
              :points="room.polygon.map((p) => `${p.x},${p.y}`).join(' ')"
              fill="rgba(44, 74, 62, 0.08)"
              stroke="transparent"
            />
          </g>
          <g v-for="wall in floorplan.walls" :key="wall.id">
            <polyline
              :points="wall.points.map((p) => `${p.x},${p.y}`).join(' ')"
              fill="none"
              stroke="#2c4a3e"
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
            >
              {{ room.name }}
            </text>
          </g>
        </svg>
        <span class="anno">底图为原图 · 半透明区域为 AI 识别房间 · 可改名称后确认</span>
      </div>
    </div>

    <aside class="editor-inspector">
      <h4>选中：{{ selectedRoom?.name ?? '—' }}</h4>
      <div v-if="selectedRoom" class="form-row">
        <label>名称</label>
        <input
          class="input light"
          :value="selectedRoom.name"
          @input="updateRoomName(($event.target as HTMLInputElement).value)"
        />
      </div>
      <div v-if="selectedRoom" class="form-row">
        <label>面积</label>
        <input class="input light" :value="selectedRoom.area ?? ''" readonly /> ㎡
      </div>
      <div v-if="selectedRoom" class="form-row">
        <label>连通</label>
        <span class="muted">{{ selectedRoom.id }}</span>
      </div>
      <p v-if="error" class="error-text">{{ error }}</p>
      <div class="inspector-actions">
        <button type="button" class="btn ghost block" @click="goBackToParse">
          ← 返回解析
        </button>
        <button type="button" class="btn ghost block subtle" @click="goBackToUpload">
          重新上传户型
        </button>
        <button
          type="button"
          class="btn primary block"
          :disabled="saving || !floorplan.rooms.length"
          @click="confirmFloorplan"
        >
          确认户型，进入设计 →
        </button>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.editor-loading,
.editor-error {
  padding: 2rem;
  text-align: center;
  color: #888;
}

.editor-error {
  color: #d48f8f;
}

.tiny {
  font-size: 0.75rem;
}

.tool:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn.block {
  width: 100%;
}

.inspector-actions {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  margin-top: 1rem;
}

.btn.subtle {
  font-size: 0.82rem;
  opacity: 0.85;
}

.error-text {
  color: #d48f8f;
  font-size: 0.85rem;
  margin: 0.75rem 0;
}

.floor-underlay {
  opacity: 0.5;
  pointer-events: none;
}
</style>
