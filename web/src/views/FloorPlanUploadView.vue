<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import { api } from '@/api/client'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))

const projectName = ref('')
const estimatedArea = ref('')
const selectedFile = ref<File | null>(null)
const previewUrl = ref<string | null>(null)
const uploading = ref(false)
const error = ref<string | null>(null)
const dragOver = ref(false)

const canSubmit = computed(() => Boolean(selectedFile.value) && !uploading.value)

function setFile(file: File | null) {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
  }
  selectedFile.value = file
  if (file && file.type.startsWith('image/')) {
    previewUrl.value = URL.createObjectURL(file)
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
      <div class="steps">
        <span class="done">1 上传</span>
        <span class="active">2 解析</span>
        <span>3 校对</span>
        <span>4 设计</span>
      </div>

      <h2>上传标准平面图</h2>
      <p class="muted">支持开发商户型图 PNG / PDF · 建议带尺寸标注</p>

      <div
        class="upload-zone"
        :class="{ 'has-file': selectedFile, 'drag-over': dragOver }"
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
        <p>{{ selectedFile ? `已选 ${selectedFile.name}` : '拖拽文件到此处，或点击选择' }}</p>
        <p class="tiny muted">最大 20MB · 将调用 oMLX VLM 解析</p>
      </div>

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

.error-text {
  color: #d48f8f;
  font-size: 0.85rem;
  margin-top: 0.75rem;
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
