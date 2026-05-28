<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, toRef, watch } from 'vue'

import FloorPlanSvg from './FloorPlanSvg.vue'
import { floorplansEqual } from './floorplanSnapshot'
import { useFloorPlanCanvas } from './useCanvas'
import { DEFAULT_ROOM_TYPE, ROOM_TYPE_GROUPS, type RoomTypeKey } from '@/constants/roomTypes'
import type { FloorPlanData } from '@/types/floorplan'

const props = defineProps<{
  projectId: number
  /** 解析完成后首次进入标注页，加载后自动保存一次 */
  autoSaveAfterParse?: boolean
}>()

const emit = defineEmits<{
  autoSaveAfterParseDone: []
}>()

const dirty = defineModel<boolean>('dirty', { default: false })

const projectId = toRef(props, 'projectId')

const {
  floorplan,
  selectedRoomId,
  selectedRoom,
  selectedVertexIndex,
  editorMode,
  cornerSnapEnabled,
  scaleDistanceM,
  scaleMarkers,
  canApplyScale,
  scaleText,
  loading,
  saving,
  error,
  isDirty,
  markDirty,
  load,
  save,
  selectRoom,
  selectVertex,
  setEditorMode,
  addScalePoint,
  resetScalePoints,
  applyScale,
  updateRoomName,
  updateRoomVertex,
  insertVertexOnSelectedEdge,
  removeSelectedVertex,
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
  isTraceActive,
  tracePoints,
  canCloseTrace,
  startPlacement,
  cancelPlacement,
  startTrace,
  cancelTrace,
  undoTracePoint,
  addTracePoint,
  finishTrace,
  startRetraceSelectedRoom,
  placeAt,
  deleteSelectedRoom,
  canDeleteRoom,
  snapshotFloorplan,
  restoreFloorplanSnapshot,
  previewSnap,
} = useFloorPlanCanvas(projectId)

const snapPreview = ref<{ point: { x: number; y: number }; kind: 'corner' | 'segment' | 'none' } | null>(null)
const traceSkipSnap = ref(false)
const preferredAnnotateMode = ref<'place-rect' | 'trace'>('place-rect')

const highlightedAnnotateMode = computed(() => {
  if (isPlacementActive.value) {
    return 'place-rect'
  }
  if (isTraceActive.value) {
    return 'trace'
  }
  return preferredAnnotateMode.value
})

function isAnnotateModeHighlighted(mode: 'place-rect' | 'trace') {
  if (editorMode.value === 'scale') {
    return false
  }
  return highlightedAnnotateMode.value === mode
}

function resetDefaultAnnotateMode() {
  preferredAnnotateMode.value = 'place-rect'
  if (isTraceActive.value) {
    cancelTrace()
  }
  if (isPlacementActive.value) {
    cancelPlacement()
  }
}

/** 全屏手动标注：高亮矩形模式并进入放置，可直接点击画布 */
function activateDefaultRectAnnotateMode() {
  beginAddRoom()
}

watch(isDirty, (value) => {
  dirty.value = value
})

const contextMenu = ref<{ x: number; y: number; point: { x: number; y: number } } | null>(null)

const pendingRoomType = ref<RoomTypeKey>(DEFAULT_ROOM_TYPE)

const previewOpen = ref(false)
const previewShowOriginal = ref(true)
const previewShowAnnotation = ref(true)
const showUnderlay = ref(true)

const fullscreenOpen = ref(false)
const fullscreenSnapshot = ref<FloorPlanData | null>(null)
const dirtyBeforeFullscreen = ref(false)

const canPreview = computed(
  () => Boolean(floorplan.value?.source_url) && !fullscreenOpen.value,
)

/** 工具栏展示用：draft 在业务上表示「已保存标注」，与「确认户型」的 confirmed 区分 */
const floorplanStatusLabel = computed(() => {
  if (!floorplan.value) {
    return '—'
  }
  if (floorplan.value.status === 'confirmed') {
    return '已确认'
  }
  if (isDirty.value) {
    return '未保存'
  }
  return '已保存'
})

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
  if (fullscreenOpen.value) {
    return
  }
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

const validationBannerTitle = computed(() => {
  if (validationLevel.value === 'error') {
    return '未通过'
  }
  if (validationIssues.value.length > 0) {
    return '有警告'
  }
  return '通过'
})

function beginAddRoom() {
  preferredAnnotateMode.value = 'place-rect'
  if (isTraceActive.value) {
    cancelTrace()
  }
  startPlacement(pendingRoomType.value)
}

function beginScaleMode() {
  preferredAnnotateMode.value = 'place-rect'
  if (isPlacementActive.value) {
    cancelPlacement()
  }
  if (isTraceActive.value) {
    cancelTrace()
  }
  setEditorMode('scale')
}

function beginTraceRoom() {
  preferredAnnotateMode.value = 'trace'
  if (isPlacementActive.value) {
    cancelPlacement()
  }
  startTrace(pendingRoomType.value)
}

function onRetraceSelectedRoom() {
  preferredAnnotateMode.value = 'trace'
  startRetraceSelectedRoom()
}

function onTraceClick(point: { x: number; y: number }) {
  addTracePoint(point, traceSkipSnap.value)
}

function onTraceMove(point: { x: number; y: number }) {
  snapPreview.value = previewSnap(point, traceSkipSnap.value)
}

function onTraceClose() {
  finishTrace()
  snapPreview.value = null
}

function addRoomTraceFromContextMenu(typeKey: RoomTypeKey) {
  if (!contextMenu.value) {
    return
  }
  preferredAnnotateMode.value = 'trace'
  startTrace(typeKey)
  contextMenu.value = null
}

function addRoomRectFromContext(typeKey: RoomTypeKey) {
  if (!contextMenu.value) {
    return
  }
  preferredAnnotateMode.value = 'place-rect'
  addRoomAtPoint(typeKey, contextMenu.value.point)
  contextMenu.value = null
}

function onContextMenu(payload: { point: { x: number; y: number }; clientX: number; clientY: number }) {
  if (!fullscreenOpen.value) {
    return
  }
  contextMenu.value = { x: payload.clientX, y: payload.clientY, point: payload.point }
}

function closeContextMenu() {
  contextMenu.value = null
}


function hasFullscreenChanges() {
  if (!fullscreenSnapshot.value || !floorplan.value) {
    return false
  }
  return !floorplansEqual(fullscreenSnapshot.value, floorplan.value)
}

function closeFullscreen() {
  cancelPlacement()
  cancelTrace()
  setEditorMode('select')
  fullscreenOpen.value = false
  fullscreenSnapshot.value = null
  document.body.style.overflow = ''
}

function enterFullscreen() {
  if (!floorplan.value || loading.value) {
    return
  }
  setEditorMode('select')
  closeContextMenu()
  dirtyBeforeFullscreen.value = isDirty.value
  fullscreenSnapshot.value = snapshotFloorplan()
  if (!fullscreenSnapshot.value) {
    return
  }
  fullscreenOpen.value = true
  document.body.style.overflow = 'hidden'
  activateDefaultRectAnnotateMode()
}

function exitFullscreenSave() {
  if (hasFullscreenChanges()) {
    markDirty()
  }
  closeFullscreen()
}

function exitFullscreenCancel() {
  if (hasFullscreenChanges() && !window.confirm('放弃全屏内的修改？')) {
    return
  }
  if (fullscreenSnapshot.value) {
    restoreFloorplanSnapshot(fullscreenSnapshot.value)
  }
  isDirty.value = dirtyBeforeFullscreen.value
  closeFullscreen()
}

function onKeydown(event: KeyboardEvent) {
  traceSkipSnap.value = event.shiftKey

  if (event.key === 'Enter' && isTraceActive.value) {
    event.preventDefault()
    finishTrace()
    snapPreview.value = null
    return
  }

  if (event.key === 'Backspace' && isTraceActive.value) {
    event.preventDefault()
    undoTracePoint()
    return
  }

  if ((event.key === 'Delete' || event.key === 'Backspace') && !isTraceActive.value && selectedVertexIndex.value != null) {
    event.preventDefault()
    removeSelectedVertex()
    return
  }

  if (event.key === 'Escape') {
    if (fullscreenOpen.value) {
      if (previewOpen.value) {
        closePreview()
        return
      }
      if (contextMenu.value) {
        closeContextMenu()
        return
      }
      if (isTraceActive.value) {
        cancelTrace()
        snapPreview.value = null
        return
      }
      if (isPlacementActive.value) {
        cancelPlacement()
        return
      }
      exitFullscreenCancel()
      return
    }
    if (previewOpen.value) {
      closePreview()
      return
    }
    if (isTraceActive.value) {
      cancelTrace()
      snapPreview.value = null
      return
    }
    if (isPlacementActive.value) {
      cancelPlacement()
    }
  }
}

onMounted(async () => {
  await load()
  resetDefaultAnnotateMode()
  if (props.autoSaveAfterParse) {
    const saved = await save()
    if (saved) {
      emit('autoSaveAfterParseDone')
    }
  }
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <div v-if="loading" class="editor-loading">加载户型数据…</div>
  <div v-else-if="error && !floorplan" class="editor-error">{{ error }}</div>
  <div v-else-if="floorplan" class="editor-shell">
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
      <div class="canvas-toolbar">
        <button type="button" class="btn sm ghost" :disabled="saving || isPlacementActive" @click="save">
          {{ saving ? '保存中…' : '保存' }}
        </button>
        <span class="muted" data-testid="floorplan-status-label">状态 · {{ floorplanStatusLabel }}</span>
        <button
          type="button"
          class="btn sm ghost canvas-toolbar-action"
          data-testid="fullscreen-annotate-btn"
          :disabled="loading || saving"
          @click="enterFullscreen"
        >
          手动标注
        </button>
      </div>
      <div
        class="floor-canvas"
        :class="{ zoomable: canPreview && editorMode === 'select' && !isPlacementActive }"
        :title="canPreview && editorMode === 'select' && !isPlacementActive ? '点击查看大图' : undefined"
      >
        <FloorPlanSvg
          :editable="false"
          :floorplan="floorplan"
          :selected-room-id="selectedRoomId"
          :show-underlay="showUnderlay"
          :underlay-opacity="0.35"
          editor-mode="select"
          @background-click="openPreview"
          @room-select="selectRoom"
        />
        <span class="anno" @click="openPreview">
          <template v-if="showUnderlay">底图为原图 · </template>
          点击房间高亮查看
          <template v-if="canPreview"> · 点击空白处查看大图</template>
          · 修改标注请使用「手动标注」
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

    <aside class="editor-inspector editor-inspector--review">
      <div class="inspector-validation" data-testid="inspector-validation">
        <div
          class="validation-panel"
          :class="validationIssues.length ? validationLevel : 'pass'"
        >
          <strong>户型质检 · {{ validationBannerTitle }}</strong>
          <ul v-if="validationIssues.length">
            <li v-for="(issue, index) in validationIssues" :key="`${issue.code}-${index}`">
              {{ issue.message }}
            </li>
          </ul>
          <p v-else class="validation-pass-hint tiny muted">当前标注数据未发现问题，可确认后进入设计。</p>
        </div>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>
      <div class="inspector-actions inspector-actions--bottom">
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
      v-if="contextMenu && fullscreenOpen"
      class="room-context-menu"
      :class="{ 'room-context-menu--elevated': fullscreenOpen }"
      :style="{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }"
      @click.stop
    >
      <p class="menu-title">新增房间</p>
      <p class="menu-hint">矩形放置</p>
      <button
        v-for="group in ROOM_TYPE_GROUPS"
        :key="`${group.group}-rect`"
        type="button"
        class="menu-group"
        disabled
      >
        {{ group.group }}
      </button>
      <template v-for="group in ROOM_TYPE_GROUPS" :key="`${group.group}-rect-opts`">
        <button
          v-for="option in group.options"
          :key="`${option.key}-rect`"
          type="button"
          class="menu-item"
          @click="addRoomRectFromContext(option.key)"
        >
          {{ option.label }}
        </button>
      </template>
      <p class="menu-hint">沿墙描边</p>
      <template v-for="group in ROOM_TYPE_GROUPS" :key="`${group.group}-trace-opts`">
        <button
          v-for="option in group.options"
          :key="`${option.key}-trace`"
          type="button"
          class="menu-item menu-item-trace"
          @click="addRoomTraceFromContextMenu(option.key)"
        >
          {{ option.label }}
        </button>
      </template>
      <button type="button" class="menu-cancel" @click="closeContextMenu">取消</button>
    </div>

    <Teleport to="body">
      <div
        v-if="fullscreenOpen"
        class="annotate-fullscreen"
        role="dialog"
        aria-modal="true"
        aria-label="全屏手动标注"
        data-testid="annotate-fullscreen-overlay"
      >
        <header class="annotate-fullscreen-head">
          <h3>手动标注</h3>
          <div class="annotate-fullscreen-head-actions">
            <label class="underlay-toggle">
              <input v-model="showUnderlay" type="checkbox" />
              原图底图
            </label>
            <button type="button" class="btn sm primary" @click="exitFullscreenSave">保存</button>
            <button type="button" class="btn sm ghost" @click="exitFullscreenCancel">取消</button>
          </div>
        </header>

        <div v-if="isPlacementActive" class="placement-banner annotate-fullscreen-banner">
          <span>在户型图上点击房间中心位置以放置「{{ pendingRoomLabel }}」</span>
          <button type="button" class="btn sm ghost" @click="cancelPlacement">取消</button>
        </div>
        <div v-else-if="isTraceActive" class="placement-banner annotate-fullscreen-banner trace-banner">
          <span>沿墙描边 · Enter 闭合 · Esc 取消</span>
          <div class="trace-banner-actions">
            <label class="underlay-toggle">
              <input v-model="cornerSnapEnabled" type="checkbox" />
              角点吸附
            </label>
            <button
              type="button"
              class="btn sm primary"
              data-testid="trace-finish-btn"
              :disabled="!canCloseTrace"
              @click="finishTrace"
            >
              闭合
            </button>
            <button type="button" class="btn sm ghost" data-testid="trace-cancel-btn" @click="cancelTrace">取消</button>
          </div>
        </div>

        <div class="annotate-fullscreen-body">
          <div class="annotate-fullscreen-canvas">
            <FloorPlanSvg
              editable
              :floorplan="floorplan"
              :selected-room-id="selectedRoomId"
              :selected-vertex-index="selectedVertexIndex"
              :show-underlay="showUnderlay"
              :underlay-opacity="0.35"
              :editor-mode="editorMode"
              :scale-markers="scaleMarkers"
              :placement-active="isPlacementActive"
              :trace-active="isTraceActive"
              :trace-points="tracePoints"
              :snap-preview="snapPreview"
              @canvas-click="onCanvasClick"
              @context-menu="onContextMenu"
              @room-select="selectRoom"
              @vertex-move="({ roomId, vertexIndex, point }) => updateRoomVertex(roomId, vertexIndex, point)"
              @vertex-select="selectVertex"
              @vertex-delete="(index) => removeSelectedVertex(index)"
              @edge-move="({ roomId, edgeIndex, delta }) => moveRoomEdge(roomId, edgeIndex, delta)"
              @edge-insert-vertex="insertVertexOnSelectedEdge"
              @trace-click="onTraceClick"
              @trace-close="onTraceClose"
              @trace-move="onTraceMove"
            />
          </div>

          <aside class="annotate-fullscreen-tools">
            <section class="fullscreen-panel fullscreen-panel--annotate">
              <h4>房间标注</h4>
              <div class="manual-room-panel">
                <label class="manual-room-field">
                  房间类型
                  <select v-model="pendingRoomType" class="input light" :disabled="isPlacementActive || isTraceActive">
                    <optgroup v-for="group in ROOM_TYPE_GROUPS" :key="group.group" :label="group.group">
                      <option v-for="option in group.options" :key="option.key" :value="option.key">
                        {{ option.label }}
                      </option>
                    </optgroup>
                  </select>
                </label>
                <button
                  type="button"
                  class="btn sm block annotate-mode-btn"
                  :class="isAnnotateModeHighlighted('place-rect') ? 'is-active' : 'is-inactive'"
                  data-testid="add-room-btn"
                  :disabled="saving"
                  @click="beginAddRoom"
                >
                  标准矩形模式
                </button>
                <button
                  type="button"
                  class="btn sm block annotate-mode-btn"
                  :class="isAnnotateModeHighlighted('trace') ? 'is-active' : 'is-inactive'"
                  data-testid="trace-room-btn"
                  :disabled="saving"
                  @click="beginTraceRoom"
                >
                  沿墙描边模式
                </button>
                <p class="tiny muted">矩形适合快速放置；描边适合 L 型、斜墙等异形房间。</p>
              </div>
            </section>

            <section class="fullscreen-panel fullscreen-panel--scale">
              <h4>比例尺</h4>
              <p class="tiny muted">{{ scaleText }}</p>
              <button
                type="button"
                class="btn sm block annotate-mode-btn"
                :class="editorMode === 'scale' ? 'is-active' : 'is-inactive'"
                data-testid="tool-scale"
                :disabled="saving"
                @click="beginScaleMode"
              >
                标定比例尺
              </button>
              <div class="scale-panel-body" :class="{ 'is-collapsed': editorMode !== 'scale' }">
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
            </section>

            <section class="fullscreen-panel fullscreen-panel--selected inspector-selected">
              <h4>选中：{{ selectedRoom?.name ?? '—' }}</h4>
              <div v-if="selectedRoom" class="form-row">
                <label>名称</label>
                <input
                  class="input light"
                  :value="selectedRoom.name"
                  :disabled="isPlacementActive || isTraceActive"
                  @input="updateRoomName(($event.target as HTMLInputElement).value)"
                />
              </div>
              <div v-if="selectedRoom" class="form-row">
                <label>面积</label>
                <input class="input light" :value="selectedRoom.area ?? ''" readonly /> ㎡
              </div>
              <button
                v-if="selectedRoom"
                type="button"
                class="btn sm ghost block"
                data-testid="retrace-room-btn"
                :disabled="isPlacementActive || isTraceActive || saving"
                @click="onRetraceSelectedRoom"
              >
                重画轮廓
              </button>
              <button
                v-if="selectedRoom"
                type="button"
                class="btn sm ghost block danger-btn"
                data-testid="delete-room-btn"
                :disabled="!canDeleteRoom || isPlacementActive || isTraceActive"
                @click="deleteSelectedRoom"
              >
                删除房间
              </button>
            </section>
          </aside>
        </div>
      </div>
    </Teleport>
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

.validation-banner.warning,
.validation-panel.warning {
  background: rgba(201, 125, 58, 0.12);
  border: 1px solid rgba(201, 125, 58, 0.35);
  color: #8a5a24;
}

.validation-banner.error,
.validation-panel.error {
  background: rgba(180, 70, 70, 0.12);
  border: 1px solid rgba(180, 70, 70, 0.35);
  color: #8f3d3d;
}

.validation-panel.pass {
  background: rgba(60, 120, 80, 0.1);
  border: 1px solid rgba(60, 120, 80, 0.35);
  color: #2d5c3e;
}

.validation-panel {
  padding: 0.75rem 0.85rem;
  border-radius: 8px;
  font-size: 0.82rem;
}

.validation-panel ul {
  margin: 0.45rem 0 0;
  padding-left: 1.1rem;
}

.validation-panel li + li {
  margin-top: 0.25rem;
}

.validation-pass-hint {
  margin: 0.45rem 0 0;
}

.editor-inspector--review {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 120px);
}

.inspector-validation {
  flex: 1;
  min-height: 0;
}

.inspector-actions--bottom {
  margin-top: auto;
  padding-top: 1rem;
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

.trace-banner {
  flex-wrap: wrap;
}

.trace-banner-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.menu-hint {
  margin: 0.35rem 0 0.15rem;
  padding: 0 0.75rem;
  font-size: 0.72rem;
  color: var(--muted);
}

.menu-item-trace {
  padding-left: 1.25rem;
}

.manual-room-panel {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  margin-bottom: 0.75rem;
}

.annotate-mode-btn {
  border: 1px solid transparent;
  border-radius: 8px;
  font-weight: 500;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}

.editor-inspector .btn.annotate-mode-btn,
.annotate-fullscreen-tools .btn.annotate-mode-btn {
  background: transparent;
}

.editor-inspector .annotate-mode-btn.is-active,
.annotate-fullscreen-tools .annotate-mode-btn.is-active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.4);
}

.editor-inspector .annotate-mode-btn.is-active:hover:not(:disabled),
.annotate-fullscreen-tools .annotate-mode-btn.is-active:hover:not(:disabled) {
  filter: brightness(1.05);
}

.editor-inspector .annotate-mode-btn.is-inactive {
  background: transparent;
  border-color: #8a8278;
  color: #2c4a3e;
}

.editor-inspector .annotate-mode-btn.is-inactive:hover:not(:disabled) {
  background: #f5f0e8;
  border-color: #2c4a3e;
  color: #1a2f28;
}

.annotate-fullscreen-tools .annotate-mode-btn.is-inactive {
  background: transparent;
  border-color: #555;
  color: #e8e4dc;
}

.annotate-fullscreen-tools .annotate-mode-btn.is-inactive:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.06);
  border-color: #777;
  color: #fff;
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

.room-context-menu--elevated {
  z-index: 2200;
}

.annotate-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  background: #1a1917;
  color: #e8e4df;
}

.annotate-fullscreen-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid #333;
  background: #242220;
}

.annotate-fullscreen-head h3 {
  margin: 0;
  font-size: 1rem;
}

.annotate-fullscreen-head-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.annotate-fullscreen-banner {
  margin: 0.65rem 1.25rem 0;
}

.annotate-fullscreen-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 0;
}

.annotate-fullscreen-canvas {
  flex: 1;
  min-width: 0;
  min-height: 0;
  padding: 1rem 1.25rem;
  display: flex;
  align-items: stretch;
  justify-content: center;
}

.annotate-fullscreen-canvas :deep(.floor-svg) {
  width: 100%;
  height: 100%;
  max-width: none;
  max-height: calc(100vh - 120px);
}

.editor-inspector {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 120px);
}

.inspector-top {
  flex: 1;
  min-height: 0;
}

.inspector-selected {
  margin-top: auto;
  padding-top: 0.85rem;
  border-top: 1px solid var(--line);
}

.inspector-selected h4 {
  margin-top: 0;
}

.annotate-fullscreen-tools {
  width: 272px;
  flex-shrink: 0;
  border-left: 1px solid #333;
  background: #242220;
  padding: 0.85rem 1rem 1rem;
  box-sizing: border-box;
  height: 100%;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0;
  font-size: 0.8rem;
  line-height: 1.4;
}

.fullscreen-panel--annotate {
  flex: 0 0 auto;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #333;
}

.fullscreen-panel--scale {
  flex: 0 0 auto;
  padding: 0.75rem 0;
  border-bottom: 1px solid #333;
}

.fullscreen-panel--selected {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-top: auto;
  padding-top: 0.75rem;
  min-height: 228px;
}

.scale-panel-body {
  height: 154px;
  box-sizing: border-box;
  margin-top: 0.4rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  flex-shrink: 0;
}

.scale-panel-body.is-collapsed {
  visibility: hidden;
  pointer-events: none;
}

.annotate-fullscreen-tools .manual-room-panel {
  gap: 0.45rem;
  margin-bottom: 0;
}

.annotate-fullscreen-tools .manual-room-panel > .tiny.muted {
  margin: 0;
  line-height: 1.35;
}

.annotate-fullscreen-tools .btn.sm.block {
  width: 100%;
  min-height: 2.35rem;
  padding: 0.45rem 0.65rem;
  line-height: 1.35;
  white-space: normal;
  text-align: center;
}

.annotate-fullscreen-tools .scale-actions {
  display: flex;
  gap: 0.4rem;
  margin-top: 0.15rem;
}

.annotate-fullscreen-tools .scale-actions .btn {
  flex: 1 1 0;
  min-width: 0;
  min-height: 2.1rem;
  padding: 0.4rem 0.5rem;
  font-size: 0.76rem;
  line-height: 1.3;
  white-space: normal;
}

.annotate-fullscreen-tools .form-row {
  margin-bottom: 0.15rem;
}

.annotate-fullscreen-tools .form-row + .btn {
  margin-top: 0.25rem;
}

.annotate-fullscreen-tools .inspector-selected {
  border-top: none;
  margin-top: 0;
  padding-top: 0;
}

.annotate-fullscreen-tools h4 {
  margin: 0 0 0.5rem;
  font-size: 0.82rem;
  line-height: 1.3;
}

.annotate-fullscreen-tools hr {
  border: none;
  border-top: 1px solid #333;
  margin: 0.85rem 0;
}

.annotate-fullscreen-tools .form-row label {
  display: block;
  font-size: 0.78rem;
  color: #888;
  margin-bottom: 0.25rem;
}
</style>
