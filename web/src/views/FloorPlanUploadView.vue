<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import ProjectStepBar from '@/components/ProjectStepBar.vue'
import { api, type FloorPlan } from '@/api/client'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))

const projectName = ref('')
const estimatedArea = ref('')
const selectedFile = ref<File | null>(null)
const previewSrc = ref<string | null>(null)
const existingFloorplan = ref<FloorPlan | null>(null)
const uploading = ref(false)
const error = ref<string | null>(null)
const dragOver = ref(false)

const hasExistingImage = computed(
  () => Boolean(existingFloorplan.value?.source_url || existingFloorplan.value?.source_image),
)

const canStartParse = computed(
  () => (hasExistingImage.value || Boolean(selectedFile.value)) && !uploading.value,
)

const existingFileLabel = computed(() => {
  if (uploading.value && selectedFile.value) {
    return `上传中… ${selectedFile.value.name}`
  }
  if (selectedFile.value) {
    return selectedFile.value.name
  }
  if (existingFloorplan.value?.original_filename) {
    return existingFloorplan.value.original_filename
  }
  if (hasExistingImage.value) {
    return '已上传户型图'
  }
  return null
})

const showPreview = computed(() => Boolean(previewSrc.value))

function isImageFile(file: File) {
  if (file.type.startsWith('image/')) {
    return true
  }
  return /\.(png|jpe?g|webp|gif)$/i.test(file.name)
}

function revokeLocalPreview() {
  if (previewSrc.value?.startsWith('blob:')) {
    URL.revokeObjectURL(previewSrc.value)
  }
}

function applyPreviewFromFloorplan(floorplan: FloorPlan) {
  revokeLocalPreview()
  previewSrc.value = floorplan.source_url ?? floorplan.source_image ?? null
}

function showLocalPreview(file: File) {
  revokeLocalPreview()
  if (isImageFile(file)) {
    previewSrc.value = URL.createObjectURL(file)
  } else {
    previewSrc.value = null
  }
}

async function uploadFile(file: File) {
  uploading.value = true
  error.value = null
  try {
    const area = estimatedArea.value.trim() ? Number(estimatedArea.value) : undefined
    const saved = await api.uploadFloorplan(projectId.value, file, {
      name: projectName.value.trim() || undefined,
      estimatedArea: Number.isFinite(area) ? area : undefined,
    })
    existingFloorplan.value = saved
    selectedFile.value = null
    applyPreviewFromFloorplan(saved)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '上传失败'
  } finally {
    uploading.value = false
  }
}

async function setFile(file: File | null) {
  selectedFile.value = file
  error.value = null
  if (!file) {
    if (existingFloorplan.value) {
      applyPreviewFromFloorplan(existingFloorplan.value)
    } else {
      revokeLocalPreview()
      previewSrc.value = null
    }
    return
  }

  showLocalPreview(file)
  await uploadFile(file)
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  void setFile(input.files?.[0] ?? null)
}

function onDrop(event: DragEvent) {
  event.preventDefault()
  dragOver.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) {
    void setFile(file)
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
    applyPreviewFromFloorplan(existingFloorplan.value)
  } catch {
    existingFloorplan.value = null
    previewSrc.value = null
  }
}

async function handleSubmit() {
  if (selectedFile.value) {
    await uploadFile(selectedFile.value)
    if (error.value) {
      return
    }
  }
  if (!hasExistingImage.value) {
    return
  }
  router.push({ name: 'floorplan-parse', params: { id: projectId.value } })
}

onMounted(loadProject)
onBeforeUnmount(revokeLocalPreview)
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="ui-page narrow upload-page">
      <ProjectStepBar :project-id="projectId" current="upload" />

      <h2>上传标准平面图</h2>
      <p class="muted">PNG / PDF · 建议带尺寸标注</p>

      <div
        class="upload-zone"
        :class="{ 'has-file': selectedFile || hasExistingImage, 'drag-over': dragOver, uploading }"
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
        <p v-if="existingFileLabel">{{ existingFileLabel }}</p>
        <p v-else>拖拽文件到此处，或点击选择</p>
        <p class="tiny muted">最大 20MB</p>
      </div>

      <div v-if="showPreview" class="preview-frame">
        <img :src="previewSrc!" alt="户型图预览" class="preview-image" />
      </div>

      <div class="meta-fields">
        <div class="form-row">
          <label for="project-name">项目名称</label>
          <input id="project-name" v-model="projectName" class="input light" />
        </div>
        <div class="form-row">
          <label for="estimated-area">预估面积（㎡，可选）</label>
          <input
            id="estimated-area"
            v-model="estimatedArea"
            class="input light"
            placeholder="89"
            inputmode="decimal"
          />
        </div>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>

      <div class="footer-actions">
        <button type="button" class="btn ghost" @click="router.push('/')">取消</button>
        <button type="button" class="btn primary" :disabled="!canStartParse" @click="handleSubmit">
          {{ uploading ? '上传中…' : '开始解析 →' }}
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

.upload-zone.uploading {
  opacity: 0.75;
  pointer-events: none;
}

.error-text {
  color: #d48f8f;
  font-size: 0.85rem;
  margin-top: 0.75rem;
}

.preview-frame {
  margin: 0.75rem 0 1rem;
  padding: 0.75rem;
  border-radius: 8px;
  background: #eee;
  min-height: 180px;
  display: grid;
  place-items: center;
}

.preview-image {
  width: 100%;
  max-height: 320px;
  object-fit: contain;
  display: block;
}

.meta-fields {
  display: grid;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
</style>
