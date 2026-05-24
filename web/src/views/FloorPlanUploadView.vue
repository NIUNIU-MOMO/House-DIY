<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import ProjectStepBar from '@/components/ProjectStepBar.vue'
import StepBackButton from '@/components/StepBackButton.vue'
import { api, type FloorPlan } from '@/api/client'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))

const projectName = ref('')
const estimatedArea = ref('')
const selectedFile = ref<File | null>(null)
const previewUrl = ref<string | null>(null)
const fileHint = ref<string | null>(null)
const existingFloorplan = ref<FloorPlan | null>(null)
const uploading = ref(false)
const error = ref<string | null>(null)
const dragOver = ref(false)

const hasExistingImage = computed(
  () => Boolean(existingFloorplan.value?.source_url || existingFloorplan.value?.source_image),
)

const canSubmit = computed(() => Boolean(selectedFile.value) && !uploading.value)

const planTypeHint = computed(() => {
  const fp = existingFloorplan.value
  if (!fp?.plan_type_label) {
    return null
  }
  return {
    label: fp.plan_type_label,
    message: fp.plan_type_message ?? '',
    isMarketing: fp.plan_type === 'marketing_color',
    hasWatermark: Boolean(fp.has_watermark),
  }
})

function setFile(file: File | null) {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
  }
  fileHint.value = null
  selectedFile.value = file
  if (!file) {
    return
  }
  if (file.type.startsWith('image/')) {
    previewUrl.value = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      const shortEdge = Math.min(img.naturalWidth, img.naturalHeight)
      if (shortEdge < 800) {
        fileHint.value = `图片短边 ${shortEdge}px，低于 800px 建议更换更高分辨率原图`
      }
    }
    img.src = previewUrl.value
    return
  }
  if (file.type === 'application/pdf') {
    fileHint.value = 'PDF 将在上传后自动栅格化；矢量 PDF 优先提取墙线区域'
  }
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  setFile(input.files?.[0] ?? null)
}

function onDrop(event: DragEvent) {
  event.preventDefault()
  dragOver.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) {
    setFile(file)
  }
}

function onDragOver(event: DragEvent) {
  event.preventDefault()
  dragOver.value = true
}

function onDragLeave() {
  dragOver.value = false
}

function openFilePicker() {
  document.getElementById('floorplan-file')?.click()
}

async function loadProject() {
  const projects = await api.listProjects()
  const project = projects.find((item) => item.id === projectId.value)
  if (project) {
    projectName.value = project.name
  }

  try {
    existingFloorplan.value = await api.getFloorplan(projectId.value)
    if (existingFloorplan.value.estimated_area != null) {
      estimatedArea.value = String(existingFloorplan.value.estimated_area)
    }
  } catch {
    existingFloorplan.value = null
  }
}

async function handleSubmit() {
  if (!selectedFile.value) {
    return
  }
  uploading.value = true
  error.value = null
  try {
    const area = estimatedArea.value.trim() ? Number(estimatedArea.value) : undefined
    await api.uploadFloorplan(projectId.value, selectedFile.value, {
      name: projectName.value.trim() || undefined,
      estimatedArea: Number.isFinite(area) ? area : undefined,
    })
    router.push({ name: 'floorplan-parse', params: { id: projectId.value } })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '上传失败'
  } finally {
    uploading.value = false
  }
}

function continueToParse() {
  router.push({ name: 'floorplan-parse', params: { id: projectId.value } })
}

onMounted(loadProject)
onBeforeUnmount(() => {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
  }
})
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="ui-page narrow upload-page">
      <ProjectStepBar :project-id="projectId" current="upload" />

      <h2>上传标准平面图</h2>
      <p class="muted">支持开发商户型图 PNG / PDF · 建议带尺寸标注</p>

      <div v-if="fileHint" class="plan-type-banner">
        <p class="plan-type-message">{{ fileHint }}</p>
      </div>

      <div v-if="planTypeHint" class="plan-type-banner" :class="{ marketing: planTypeHint.isMarketing }">
        <p class="plan-type-title">已识别：{{ planTypeHint.label }}</p>
        <p class="plan-type-message">{{ planTypeHint.message }}</p>
        <p v-if="planTypeHint.hasWatermark" class="plan-type-tip">
          中央水印将在解析时忽略，建议使用墙体线稿而非色块边界校对。
        </p>
        <p v-else-if="planTypeHint.isMarketing" class="plan-type-tip">
          彩色户型图将按墙体围合解析，请在校对页重点检查房间轮廓是否贴墙。
        </p>
        <p v-else class="plan-type-tip">
          线稿模式优先识别墙体与标注，适合 CAD 导出图。
        </p>
      </div>

      <div v-if="hasExistingImage && !selectedFile" class="existing-banner">
        <p>已上传户型图，可直接继续解析，或重新选择文件覆盖。</p>
        <button type="button" class="btn primary sm" @click="continueToParse">继续解析 →</button>
      </div>

      <div
        class="upload-zone"
        :class="{ 'has-file': selectedFile || hasExistingImage, 'drag-over': dragOver }"
        role="button"
        tabindex="0"
        @click="openFilePicker"
        @drop="onDrop"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @keydown.enter="openFilePicker"
      >
        <input
          id="floorplan-file"
          type="file"
          accept="image/png,image/jpeg,application/pdf"
          hidden
          @change="onFileChange"
        />
        <div class="upload-icon">↑</div>
        <p v-if="selectedFile">已选 {{ selectedFile.name }}</p>
        <p v-else-if="hasExistingImage">已上传 · 点击或拖拽可更换文件</p>
        <p v-else>拖拽文件到此处，或点击选择</p>
        <p class="tiny muted">最大 20MB · 将调用 oMLX VLM 解析</p>
      </div>

      <img
        v-if="!previewUrl && existingFloorplan?.source_url"
        :src="existingFloorplan.source_url"
        alt="已上传户型"
        class="existing-preview"
      />

      <div class="form-row">
        <label for="project-name">项目名称</label>
        <input id="project-name" v-model="projectName" class="input light" />
      </div>

      <div class="form-row">
        <label for="estimated-area">预估总面积（㎡，可选）</label>
        <input
          id="estimated-area"
          v-model="estimatedArea"
          class="input light"
          placeholder="89"
          inputmode="decimal"
        />
      </div>

      <div v-if="selectedFile" class="preview-strip">
        <img v-if="previewUrl" :src="previewUrl" alt="预览" class="preview-thumb" />
        <div v-else class="preview-thumb pdf">PDF</div>
        <span>已选 {{ selectedFile.name }}</span>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>

      <div class="footer-actions">
        <button type="button" class="btn ghost" @click="router.push('/')">取消</button>
        <button
          type="button"
          class="btn primary"
          :disabled="!canSubmit"
          @click="handleSubmit"
        >
          {{ uploading ? '上传中…' : '上传并开始解析 →' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.upload-page h2 {
  font-family: var(--serif);
  font-size: 1.5rem;
  margin-bottom: 0.35rem;
}

.tiny {
  font-size: 0.75rem;
  margin-top: 0.35rem;
}

.error-text {
  color: #d48f8f;
  font-size: 0.85rem;
  margin-top: 0.75rem;
}

.existing-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  background: #2c4a3e;
  color: #c8ead4;
  border-radius: 8px;
  padding: 0.65rem 0.85rem;
  margin-bottom: 1rem;
  font-size: 0.85rem;
}

.plan-type-banner {
  background: #eef3f8;
  border: 1px solid #d0dce8;
  border-radius: 8px;
  padding: 0.75rem 0.9rem;
  margin-bottom: 1rem;
  font-size: 0.85rem;
}

.plan-type-banner.marketing {
  background: #f5f0e8;
  border-color: #e0d4c0;
}

.plan-type-title {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.plan-type-message {
  color: var(--muted);
  margin-bottom: 0.35rem;
}

.plan-type-tip {
  font-size: 0.8rem;
  color: #5a6a7a;
}

.existing-preview {
  width: 100%;
  max-height: 180px;
  object-fit: contain;
  border-radius: 8px;
  margin-bottom: 1rem;
  background: #eee;
}

.preview-thumb {
  width: 56px;
  height: 56px;
  object-fit: cover;
  border-radius: 6px;
  background: #eee;
}

.preview-thumb.pdf {
  display: grid;
  place-items: center;
  font-size: 0.72rem;
  color: var(--muted);
}
</style>
