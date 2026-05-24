<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, toRef } from 'vue'

import FloorPlanSvg from './FloorPlanSvg.vue'
import { useFloorPlanCanvas } from './useCanvas'

const props = defineProps<{
  projectId: number
}>()

const projectId = toRef(props, 'projectId')

const {
  floorplan,
  selectedRoomId,
  selectedRoom,
  scaleText,
  loading,
  saving,
  error,
  load,
  save,
  selectRoom,
  updateRoomName,
  roomLabel,
  confirmFloorplan,
  validationLevel,
  validationIssues,
  hasValidationError,
  canConfirm,
} = useFloorPlanCanvas(projectId)

const previewOpen = ref(false)
const previewMode = ref<'original' | 'annotated'>('annotated')
const showUnderlay = ref(true)

const canPreview = computed(() => Boolean(floorplan.value?.source_url))

function openPreview() {
  if (canPreview.value) {
    previewMode.value = 'annotated'
    previewOpen.value = true
  }
}

function closePreview() {
  previewOpen.value = false
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && previewOpen.value) {
    closePreview()
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
      <button type="button" class="tool active">选择</button>
      <button type="button" class="tool" disabled>墙线</button>
      <button type="button" class="tool" disabled>门洞</button>
      <button type="button" class="tool" disabled>窗户</button>
      <hr />
      <h4>比例尺</h4>
      <p class="tiny muted">{{ scaleText }}</p>
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
        <button type="button" class="btn sm ghost" :disabled="saving" @click="save">
          {{ saving ? '保存中…' : '保存' }}
        </button>
        <span class="muted">状态 · {{ floorplan.status }}</span>
      </div>
      <div
        class="floor-canvas"
        :class="{ zoomable: canPreview }"
        :title="canPreview ? '点击查看大图' : undefined"
        @click="openPreview"
      >
        <FloorPlanSvg
          :floorplan="floorplan"
          :selected-room-id="selectedRoomId"
          :show-underlay="showUnderlay"
          :underlay-opacity="0.35"
        />
        <span class="anno">
          <template v-if="showUnderlay">底图为原图 · </template>
          色块为 AI 识别房间 · 选中房间高亮 · 可改名称后确认
          <template v-if="canPreview"> · 点击画布查看大图</template>
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
            <h3>{{ previewMode === 'original' ? '户型原图' : 'AI 标注图' }}</h3>
            <div class="preview-tabs">
              <button
                type="button"
                class="preview-tab"
                :class="{ active: previewMode === 'original' }"
                @click="previewMode = 'original'"
              >
                原图
              </button>
              <button
                type="button"
                class="preview-tab"
                :class="{ active: previewMode === 'annotated' }"
                @click="previewMode = 'annotated'"
              >
                标注图
              </button>
            </div>
          </div>
          <button type="button" class="icon-btn-close" aria-label="关闭" @click="closePreview">×</button>
        </header>
        <div class="image-preview-body">
          <img
            v-if="previewMode === 'original'"
            :src="floorplan.source_url"
            alt="户型原图"
            class="image-preview-img"
          />
          <FloorPlanSvg
            v-else
            class="preview-svg"
            :floorplan="floorplan"
            :selected-room-id="selectedRoomId"
            :show-underlay="false"
            :label-scale="1.15"
          />
        </div>
        <footer v-if="previewMode === 'annotated'" class="image-preview-foot">
          <span class="tiny muted">仅显示 AI 识别轮廓与房间名，不含原图文字</span>
        </footer>
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
        <button
          type="button"
          class="btn primary block"
          :disabled="!canConfirm"
          @click="confirmFloorplan"
        >
          确认户型，进入设计 →
        </button>
        <p v-if="hasValidationError" class="tiny warn-text">
          存在严重质检问题，请修正房间边界或重新解析后再确认
        </p>
      </div>
    </aside>
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
</style>
