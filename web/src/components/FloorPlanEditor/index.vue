<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, toRef, watch } from 'vue'

import FloorPlanSvg from './FloorPlanSvg.vue'
import { useFloorPlanCanvas } from './useCanvas'
import { DEFAULT_ROOM_TYPE, ROOM_TYPE_GROUPS, type RoomTypeKey } from '@/constants/roomTypes'

const props = defineProps<{
  projectId: number
}>()

const dirty = defineModel<boolean>('dirty', { default: false })

const projectId = toRef(props, 'projectId')

const {
  floorplan,
  selectedRoomId,
  selectedRoom,
  editorMode,
  scaleDistanceM,
  scaleMarkers,
  canApplyScale,
  scaleText,
  loading,
  saving,
  error,
  isDirty,
  load,
  save,
  selectRoom,
  setEditorMode,
  addScalePoint,
  resetScalePoints,
  applyScale,
  updateRoomName,
  updateRoomVertex,
  moveRoomEdge,
  addRoomAtPoint,
  roomLabel,
  confirmFloorplan,
  validationLevel,
  validationIssues,
  hasValidationError,
  canConfirm,
  placementMode,
  isPlacementActive,
  startPlacement,
  cancelPlacement,
  placeAt,
  deleteSelectedRoom,
  canDeleteRoom,
} = useFloorPlanCanvas(projectId)

watch(isDirty, (value) => {
  dirty.value = value
})

const contextMenu = ref<{ x: number; y: number; point: { x: number; y: number } } | null>(null)

const pendingRoomType = ref<RoomTypeKey>(DEFAULT_ROOM_TYPE)

const previewOpen = ref(false)
const previewShowOriginal = ref(true)
const previewShowAnnotation = ref(true)
const showUnderlay = ref(true)

const canPreview = computed(() => Boolean(floorplan.value?.source_url))

const previewTitle = computed(() => {
  if (previewShowOriginal.value && previewShowAnnotation.value) {
    return '原图 + 标注'
  }
  if (previewShowOriginal.value) {
    return '户型原图'
  }
  if (previewShowAnnotation.value) {
    return 'AI 标注'
  }
  return '户型大图'
})

const previewFootnote = computed(() => {
  if (previewShowOriginal.value && previewShowAnnotation.value) {
    return '原图底图与 AI 标注轮廓叠加显示，与校对页一致'
  }
  if (previewShowOriginal.value) {
    return '仅显示上传的户型原图'
  }
  if (previewShowAnnotation.value) {
    return '仅显示 AI 识别轮廓与房间名'
  }
  return '请至少勾选「原图」或「标注」'
})

const pendingRoomLabel = computed(() => {
  for (const group of ROOM_TYPE_GROUPS) {
    const option = group.options.find((item) => item.key === pendingRoomType.value)
    if (option) {
      return option.label
    }
  }
  return '房间'
})

function openPreview() {
  if (canPreview.value && editorMode.value === 'select' && !isPlacementActive.value) {
    previewShowOriginal.value = true
    previewShowAnnotation.value = true
    previewOpen.value = true
  }
}

function setPreviewShowOriginal(checked: boolean) {
  if (!checked && !previewShowAnnotation.value) {
    return
  }
  previewShowOriginal.value = checked
}

function setPreviewShowAnnotation(checked: boolean) {
  if (!checked && !previewShowOriginal.value) {
    return
  }
  previewShowAnnotation.value = checked
}

function closePreview() {
  previewOpen.value = false
}

function onCanvasClick(point: { x: number; y: number }) {
  if (isPlacementActive.value) {
    placeAt(point)
    return
  }
  addScalePoint(point)
}

function beginAddRoom() {
  startPlacement(pendingRoomType.value)
}

function onContextMenu(payload: { point: { x: number; y: number }; clientX: number; clientY: number }) {
  contextMenu.value = { x: payload.clientX, y: payload.clientY, point: payload.point }
}

function closeContextMenu() {
  contextMenu.value = null
}

function addRoomFromContext(typeKey: RoomTypeKey) {
  if (!contextMenu.value) {
    return
  }
  addRoomAtPoint(typeKey, contextMenu.value.point)
  contextMenu.value = null
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    if (previewOpen.value) {
      closePreview()
      return
    }
    if (isPlacementActive.value) {
      cancelPlacement()
    }
  }
}

onMounted(() => {
  void load()
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div v-if="loading" class="editor-loading">加载户型数据…</div>
  <div v-else-if="error && !floorplan" class="editor-error">{{ error }}</div>
  <div v-else-if="floorplan" class="editor-shell">
    <div
      v-if="validationIssues.length"
      class="validation-banner"
      :class="validationLevel"
    >
      <strong>户型质检 · {{ validationLevel === 'error' ? '未通过' : '有警告' }}</strong>
      <ul>
        <li v-for="(issue, index) in validationIssues" :key="`${issue.code}-${index}`">
          {{ issue.message }}
        </li>
      </ul>
    </div>
    <div class="editor-layout">
    <aside class="editor-tools">
      <h4>工具</h4>
      <button
        type="button"
        class="tool"
        :class="{ active: editorMode === 'select' }"
        data-testid="tool-select"
        @click="setEditorMode('select')"
      >
        选择
      </button>
      <button
        type="button"
        class="tool"
        :class="{ active: editorMode === 'scale' }"
        data-testid="tool-scale"
        @click="setEditorMode('scale')"
      >
        标定比例尺
      </button>
      <button type="button" class="tool" disabled>墙线</button>
      <button type="button" class="tool" disabled>门洞</button>
      <button type="button" class="tool" disabled>窗户</button>
      <hr />
      <h4>比例尺</h4>
      <p class="tiny muted">{{ scaleText }}</p>
      <div v-if="editorMode === 'scale'" class="scale-panel">
        <p class="tiny muted">在画布上依次点击两点（A → B）</p>
        <label class="scale-field">
          实际距离（米）
          <input
            v-model="scaleDistanceM"
            class="input light"
            type="number"
            min="0.1"
            step="0.1"
            placeholder="例如 3.6"
            data-testid="scale-distance-input"
          />
        </label>
        <div class="scale-actions">
          <button
            type="button"
            class="btn sm primary"
            :disabled="!canApplyScale || saving"
            data-testid="apply-scale-btn"
            @click="applyScale"
          >
            应用比例尺
          </button>
          <button type="button" class="btn sm ghost" @click="resetScalePoints">重置选点</button>
        </div>
      </div>
      <hr />
      <h4>显示</h4>
      <label class="underlay-toggle">
        <input v-model="showUnderlay" type="checkbox" />
        显示原图底图
      </label>
      <p class="tiny muted">关闭后仅看 AI 标注轮廓与名称</p>
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
      <div v-if="isPlacementActive" class="placement-banner">
        <span>在户型图上点击房间中心位置以放置「{{ pendingRoomLabel }}」</span>
        <button type="button" class="btn sm ghost" @click="cancelPlacement">取消</button>
      </div>
      <div class="canvas-toolbar">
        <button type="button" class="btn sm ghost" :disabled="saving || isPlacementActive" @click="save">
          {{ saving ? '保存中…' : '保存' }}
        </button>
        <span class="muted">状态 · {{ floorplan.status }}</span>
      </div>
      <div
        class="floor-canvas"
        :class="{ zoomable: canPreview && editorMode === 'select' && !isPlacementActive }"
        :title="canPreview && editorMode === 'select' && !isPlacementActive ? '点击查看大图' : undefined"
      >
        <FloorPlanSvg
          editable
          :floorplan="floorplan"
          :selected-room-id="selectedRoomId"
          :show-underlay="showUnderlay"
          :underlay-opacity="0.35"
          :editor-mode="editorMode"
          :scale-markers="scaleMarkers"
          :placement-active="isPlacementActive"
          @canvas-click="onCanvasClick"
          @background-click="openPreview"
          @context-menu="onContextMenu"
          @room-select="selectRoom"
          @vertex-move="({ roomId, vertexIndex, point }) => updateRoomVertex(roomId, vertexIndex, point)"
          @edge-move="({ roomId, edgeIndex, delta }) => moveRoomEdge(roomId, edgeIndex, delta)"
        />
        <span class="anno" @click="openPreview">
          <template v-if="isPlacementActive">放置模式：点击画布确定新房间中心，Esc 或「取消」退出</template>
          <template v-else-if="editorMode === 'scale'">比例尺模式：点击画布选两点，输入实际距离后应用</template>
          <template v-else>
            <template v-if="showUnderlay">底图为原图 · </template>
            拖拽选中房间顶点可修正轮廓 · 改名称后保存或确认
            <template v-if="canPreview"> · 点击画布查看大图</template>
          </template>
        </span>
      </div>
    </div>

    <div
      v-if="previewOpen && floorplan.source_url"
      class="image-preview-backdrop"
      @click.self="closePreview"
    >
      <div class="image-preview-dialog" role="dialog" aria-modal="true" aria-label="户型大图">
        <header class="image-preview-head">
          <div class="preview-head-left">
            <h3>{{ previewTitle }}</h3>
            <div class="preview-layer-toggles">
              <label class="preview-layer-toggle">
                <input
                  type="checkbox"
                  :checked="previewShowOriginal"
                  data-testid="preview-toggle-original"
                  @change="setPreviewShowOriginal(($event.target as HTMLInputElement).checked)"
                />
                原图
              </label>
              <label class="preview-layer-toggle">
                <input
                  type="checkbox"
                  :checked="previewShowAnnotation"
                  data-testid="preview-toggle-annotation"
                  @change="setPreviewShowAnnotation(($event.target as HTMLInputElement).checked)"
                />
                标注
              </label>
            </div>
          </div>
          <button type="button" class="icon-btn-close" aria-label="关闭" @click="closePreview">×</button>
        </header>
        <div class="image-preview-body">
          <p v-if="!previewShowOriginal && !previewShowAnnotation" class="preview-empty muted">
            请至少勾选「原图」或「标注」
          </p>
          <img
            v-else-if="previewShowOriginal && !previewShowAnnotation"
            :src="floorplan.source_url"
            alt="户型原图"
            class="image-preview-img"
          />
          <FloorPlanSvg
            v-else-if="previewShowAnnotation"
            class="preview-svg"
            :floorplan="floorplan"
            :selected-room-id="selectedRoomId"
            :show-underlay="previewShowOriginal"
            :underlay-opacity="0.35"
            :label-scale="1.15"
          />
        </div>
        <footer class="image-preview-foot">
          <span class="tiny muted">{{ previewFootnote }}</span>
        </footer>
      </div>
    </div>

    <aside class="editor-inspector">
      <h4>手动标注</h4>
      <div class="manual-room-panel">
        <label class="manual-room-field">
          房间类型
          <select v-model="pendingRoomType" class="input light" :disabled="isPlacementActive">
            <optgroup v-for="group in ROOM_TYPE_GROUPS" :key="group.group" :label="group.group">
              <option v-for="option in group.options" :key="option.key" :value="option.key">
                {{ option.label }}
              </option>
            </optgroup>
          </select>
        </label>
        <button
          type="button"
          class="btn sm primary block"
          data-testid="add-room-btn"
          :disabled="isPlacementActive || saving"
          @click="beginAddRoom"
        >
          + 新增房间
        </button>
        <p class="tiny muted">选择类型后，在画布上右键或点击中心位置放置默认矩形，再拖拽顶点/边线微调</p>
      </div>

      <hr />

      <h4>选中：{{ selectedRoom?.name ?? '—' }}</h4>
      <div v-if="selectedRoom" class="form-row">
        <label>名称</label>
        <input
          class="input light"
          :value="selectedRoom.name"
          :disabled="isPlacementActive"
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
      <button
        v-if="selectedRoom"
        type="button"
        class="btn sm ghost block danger-btn"
        data-testid="delete-room-btn"
        :disabled="!canDeleteRoom"
        @click="deleteSelectedRoom"
      >
        删除房间
      </button>
      <p v-if="error" class="error-text">{{ error }}</p>
      <div class="inspector-actions">
        <button
          type="button"
          class="btn primary block"
          :disabled="!canConfirm"
          data-testid="confirm-floorplan-btn"
          @click="confirmFloorplan"
        >
          确认户型，进入设计 →
        </button>
        <p v-if="hasValidationError" class="tiny warn-text">
          存在严重质检问题，请修正房间边界或重新解析后再确认
        </p>
      </div>
    </aside>
    <div
      v-if="contextMenu"
      class="room-context-menu"
      :style="{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }"
      @click.stop
    >
      <p class="menu-title">新增房间</p>
      <button
        v-for="group in ROOM_TYPE_GROUPS"
        :key="group.group"
        type="button"
        class="menu-group"
        disabled
      >
        {{ group.group }}
      </button>
      <template v-for="group in ROOM_TYPE_GROUPS" :key="`${group.group}-opts`">
        <button
          v-for="option in group.options"
          :key="option.key"
          type="button"
          class="menu-item"
          @click="addRoomFromContext(option.key)"
        >
          {{ option.label }}
        </button>
      </template>
      <button type="button" class="menu-cancel" @click="closeContextMenu">取消</button>
    </div>
  </div>
  </div>
</template>

<style scoped>
.editor-shell {
  padding: 0 1.5rem 1rem;
}

.validation-banner {
  margin: 0 0 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.82rem;
}

.validation-banner.error {
  background: rgba(180, 70, 70, 0.12);
  border: 1px solid rgba(180, 70, 70, 0.35);
  color: #8f3d3d;
}

.validation-banner.warning {
  background: rgba(201, 125, 58, 0.12);
  border: 1px solid rgba(201, 125, 58, 0.35);
  color: #8a5a24;
}

.validation-banner ul {
  margin: 0.45rem 0 0;
  padding-left: 1.1rem;
}

.validation-banner li + li {
  margin-top: 0.25rem;
}

.warn-text {
  color: #8a5a24;
  margin: 0;
}

.placement-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.65rem;
  padding: 0.55rem 0.75rem;
  border-radius: 8px;
  background: rgba(201, 125, 58, 0.12);
  border: 1px solid rgba(201, 125, 58, 0.35);
  font-size: 0.82rem;
  color: #8a5a24;
}

.manual-room-panel {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  margin-bottom: 0.75rem;
}

.manual-room-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.78rem;
}

.danger-btn {
  color: #d48f8f;
  border-color: #5a3a3a;
  margin-top: 0.5rem;
}

.danger-btn:hover:not(:disabled) {
  background: rgba(212, 143, 143, 0.12);
}

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

.tool.active {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(201, 125, 58, 0.1);
}

.scale-panel {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  margin-top: 0.5rem;
}

.scale-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.78rem;
}

.scale-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.underlay-toggle {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.82rem;
  cursor: pointer;
  margin-bottom: 0.35rem;
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

.error-text {
  color: #d48f8f;
  font-size: 0.85rem;
  margin: 0.75rem 0;
}

.floor-canvas.zoomable {
  cursor: zoom-in;
}

.image-preview-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.image-preview-dialog {
  width: min(1200px, 100%);
  max-height: min(92vh, 960px);
  background: #1e1c18;
  border: 1px solid #444;
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
}

.image-preview-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid #333;
}

.preview-head-left {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.image-preview-head h3 {
  font-size: 0.95rem;
  margin: 0;
}

.preview-tabs {
  display: flex;
  gap: 0.35rem;
}

.preview-layer-toggles {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.preview-layer-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.82rem;
  color: #ccc;
  cursor: pointer;
}

.preview-layer-toggle input {
  accent-color: var(--accent);
}

.preview-empty {
  padding: 2rem 1rem;
  text-align: center;
}

.preview-tab {
  border: 1px solid #555;
  background: transparent;
  color: #bbb;
  border-radius: 6px;
  padding: 0.25rem 0.65rem;
  font-size: 0.78rem;
  cursor: pointer;
  font-family: inherit;
}

.preview-tab.active {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(201, 125, 58, 0.12);
}

.icon-btn-close {
  border: none;
  background: transparent;
  color: #aaa;
  font-size: 1.5rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 0.25rem;
}

.image-preview-body {
  flex: 1;
  overflow: auto;
  padding: 1rem;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.image-preview-img {
  max-width: 100%;
  height: auto;
  display: block;
  background: #fff;
  border-radius: 4px;
}

.preview-svg {
  max-width: 100%;
}

.preview-svg :deep(.floor-svg) {
  max-width: none;
  width: min(1100px, 100%);
}

.image-preview-foot {
  padding: 0.55rem 1rem;
  border-top: 1px solid #333;
}

.room-context-menu {
  position: fixed;
  z-index: 1200;
  min-width: 140px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  padding: 0.35rem 0;
}

.menu-title {
  font-size: 0.72rem;
  color: var(--muted);
  padding: 0.35rem 0.65rem;
}

.menu-group {
  display: block;
  width: 100%;
  text-align: left;
  border: none;
  background: #f5f0e8;
  color: var(--muted);
  font-size: 0.68rem;
  padding: 0.25rem 0.65rem;
  cursor: default;
}

.menu-item {
  display: block;
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  padding: 0.4rem 0.65rem;
  font-size: 0.82rem;
  cursor: pointer;
}

.menu-item:hover {
  background: #f0ebe3;
}

.menu-cancel {
  display: block;
  width: 100%;
  border: none;
  border-top: 1px solid var(--line);
  background: transparent;
  padding: 0.45rem 0.65rem;
  font-size: 0.78rem;
  color: var(--muted);
  cursor: pointer;
}
</style>
