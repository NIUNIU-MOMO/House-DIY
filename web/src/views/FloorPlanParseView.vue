<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import ProjectStepBar from '@/components/ProjectStepBar.vue'
import { api, type Task } from '@/api/client'
import { useTaskWebSocket } from '@/composables/useTaskWebSocket'
import { PARSE_STEP_LABELS } from '@/types/task'
import {
  maxStepToProjectStep,
  resolveMaxCompletedStepIndex,
  stepIndex,
} from '@/utils/projectNavigation'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))

const task = ref<Task | null>(null)
const error = ref<string | null>(null)
const starting = ref(false)
const cancelling = ref(false)
const hasPassedParse = ref(false)
const isReparseSession = ref(false)
const hadSavedAnnotationBeforeReparse = ref(false)
const annotationBackup = ref<Record<string, unknown> | null>(null)
const logPanelRef = ref<HTMLElement | null>(null)

const progress = computed(() => Math.round(task.value?.progress ?? 0))
const isParseActive = computed(
  () => task.value?.status === 'pending' || task.value?.status === 'running',
)
const taskLogs = computed(() => task.value?.logs ?? [])

const statusTitle = computed(() => {
  if (task.value?.status === 'failed') {
    return '解析失败'
  }
  if (isParseActive.value) {
    return '正在解析户型…'
  }
  if (task.value?.status === 'done') {
    return '解析已完成'
  }
  return '正在解析户型…'
})

const showSpinner = computed(() => isParseActive.value)

const showReparseButton = computed(() => hasPassedParse.value && !isParseActive.value)

function stepClass(index: number) {
  if (!task.value) {
    return index === 0 ? 'active' : ''
  }
  if (task.value.status === 'done') {
    return 'done'
  }
  if (index < task.value.step) {
    return 'done'
  }
  if (index === task.value.step) {
    return task.value.status === 'failed' ? '' : 'active'
  }
  return ''
}

function stepIcon(index: number) {
  const cls = stepClass(index)
  if (cls === 'done') {
    return '✓'
  }
  if (cls === 'active') {
    return '◐'
  }
  return '○'
}

function scrollLogsToBottom() {
  nextTick(() => {
    const panel = logPanelRef.value
    if (panel) {
      panel.scrollTop = panel.scrollHeight
    }
  })
}

function projectHasSavedAnnotation(maxStep: string) {
  return stepIndex(maxStepToProjectStep(maxStep)) >= stepIndex('annotate')
}

function showIdleCompletedTask() {
  const lastLabel = PARSE_STEP_LABELS[PARSE_STEP_LABELS.length - 1] ?? ''
  task.value = {
    id: 0,
    project_id: projectId.value,
    type: 'floorplan_parse',
    status: 'done',
    progress: 100,
    step: PARSE_STEP_LABELS.length - 1,
    step_label: lastLabel,
    error: null,
    logs: [],
  }
}

async function restoreAnnotationBackup() {
  if (!annotationBackup.value) {
    return
  }
  try {
    await api.saveFloorplanAnnotation(projectId.value, annotationBackup.value)
    annotationBackup.value = null
    error.value = null
  } catch (e) {
    error.value = e instanceof Error ? e.message : '恢复标注失败'
  }
}

async function handleParseDone() {
  if (isReparseSession.value && hadSavedAnnotationBeforeReparse.value) {
    const overwrite = window.confirm(
      '是否覆盖已保存的标注结果？\n\n确定：使用本次解析结果覆盖并自动保存。\n取消：放弃本次解析，保留原有标注。',
    )
    isReparseSession.value = false
    if (overwrite) {
      router.push({
        name: 'floorplan-editor',
        params: { id: projectId.value },
        query: { fromParse: '1' },
      })
      return
    }
    await restoreAnnotationBackup()
    showIdleCompletedTask()
    return
  }

  router.push({
    name: 'floorplan-editor',
    params: { id: projectId.value },
    query: { fromParse: '1' },
  })
}

function handleTaskUpdate(next: Task) {
  task.value = next
  scrollLogsToBottom()
  if (next.status === 'done') {
    setTimeout(() => {
      void handleParseDone()
    }, 600)
  }
  if (next.status === 'failed') {
    error.value = next.error ?? '解析失败'
  }
  if (next.status === 'cancelled') {
    router.replace({ name: 'floorplan-upload', params: { id: projectId.value } })
  }
}

useTaskWebSocket(() => projectId.value, handleTaskUpdate)

async function pollTask(taskId: number) {
  const current = await api.getTask(projectId.value, taskId)
  handleTaskUpdate(current)
  if (current.status === 'pending' || current.status === 'running') {
    window.setTimeout(() => pollTask(taskId), 1000)
  }
}

async function startParse() {
  starting.value = true
  error.value = null
  try {
    const project = await api.getProject(projectId.value)
    const isReparse = hasPassedParse.value || stepIndex(maxStepToProjectStep(project.max_step)) > stepIndex('parse')
    isReparseSession.value = isReparse
    hadSavedAnnotationBeforeReparse.value = projectHasSavedAnnotation(project.max_step)
    if (isReparse && hadSavedAnnotationBeforeReparse.value) {
      annotationBackup.value = (await api.getFloorplan(projectId.value)) as Record<string, unknown>
    } else {
      annotationBackup.value = null
    }

    const created = await api.startFloorplanParse(projectId.value)
    task.value = created
    pollTask(created.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '无法启动解析'
    isReparseSession.value = false
  } finally {
    starting.value = false
  }
}

async function cancelParse() {
  if (!task.value || cancelling.value) {
    return
  }
  cancelling.value = true
  error.value = null
  try {
    const cancelled = await api.cancelTask(projectId.value, task.value.id)
    handleTaskUpdate(cancelled)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '取消失败'
  } finally {
    cancelling.value = false
  }
}

watch(taskLogs, scrollLogsToBottom)

onMounted(async () => {
  const project = await api.getProject(projectId.value)
  const maxIdx = await resolveMaxCompletedStepIndex(projectId.value, project)
  hasPassedParse.value = maxIdx > stepIndex('parse')

  if (hasPassedParse.value) {
    showIdleCompletedTask()
    return
  }

  if (project.status === 'draft') {
    try {
      const floorplan = await api.getFloorplan(projectId.value)
      if (!floorplan.source_url && !floorplan.source_image) {
        router.replace({ name: 'floorplan-upload', params: { id: projectId.value } })
        return
      }
    } catch {
      router.replace({ name: 'floorplan-upload', params: { id: projectId.value } })
      return
    }
  }

  await startParse()
})
</script>

<template>
  <div>
    <AppHeader active="projects" :locked="isParseActive" />
    <div class="ui-page narrow center parse-page">
      <ProjectStepBar :project-id="projectId" current="parse" :locked="isParseActive" />

      <div class="parse-toolbar">
        <button
          v-if="isParseActive"
          type="button"
          class="btn ghost sm cancel-btn"
          :disabled="cancelling"
          @click="cancelParse"
        >
          {{ cancelling ? '取消中…' : '取消解析' }}
        </button>
        <button
          v-else-if="showReparseButton"
          type="button"
          class="btn ghost sm"
          :disabled="starting"
          @click="startParse"
        >
          {{ starting ? '启动中…' : '重新解析' }}
        </button>
      </div>

      <div class="loader-card">
        <div v-if="showSpinner" class="spinner" />
        <h2>{{ statusTitle }}</h2>
        <p class="muted progress-text">{{ progress }}%</p>

        <ul class="task-list">
          <li
            v-for="(label, index) in PARSE_STEP_LABELS"
            :key="label"
            :class="stepClass(index)"
          >
            {{ stepIcon(index) }} {{ label }}
          </li>
        </ul>

        <div v-if="taskLogs.length > 0" class="log-panel-wrap">
          <p class="log-title">处理日志</p>
          <div ref="logPanelRef" class="log-panel" role="log" aria-live="polite">
            <p v-for="(line, index) in taskLogs" :key="`${index}-${line}`" class="log-line">
              {{ line }}
            </p>
          </div>
        </div>

        <p v-if="error" class="error-text">{{ error }}</p>
        <button
          v-if="task?.status === 'failed'"
          type="button"
          class="btn primary"
          :disabled="starting"
          @click="startParse"
        >
          重试解析
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.parse-page {
  padding-top: 2rem;
}

.parse-toolbar {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 0.75rem;
  min-height: 2rem;
}

.cancel-btn {
  color: #d48f8f;
  border-color: #5a3a3a;
}

.cancel-btn:hover:not(:disabled) {
  background: rgba(212, 143, 143, 0.12);
}

.loader-card {
  background: var(--bg-panel);
  border: 1px solid #333;
  border-radius: var(--radius);
  padding: 2rem 1.5rem;
  text-align: center;
}

.loader-card h2 {
  font-family: var(--serif);
  margin-bottom: 0.35rem;
}

.progress-text {
  margin-bottom: 1rem;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 3px solid #333;
  border-top-color: var(--accent);
  border-radius: 50%;
  margin: 0 auto 1rem;
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.task-list {
  list-style: none;
  text-align: left;
  max-width: 320px;
  margin: 0 auto 1rem;
}

.task-list li {
  padding: 0.35rem 0;
  color: #888;
}

.task-list li.done {
  color: #8fd4a8;
}

.task-list li.active {
  color: var(--accent);
  font-weight: 500;
}

.log-panel-wrap {
  text-align: left;
  max-width: 520px;
  margin: 0 auto 1rem;
}

.log-title {
  font-size: 0.78rem;
  color: #888;
  margin-bottom: 0.35rem;
}

.log-panel {
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 0.65rem 0.75rem;
  max-height: 180px;
  overflow-y: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.72rem;
  line-height: 1.45;
}

.log-line {
  margin: 0;
  color: #b8b8b8;
  word-break: break-word;
}

.log-line + .log-line {
  margin-top: 0.2rem;
}

.error-text {
  color: #d48f8f;
  margin: 1rem 0;
  font-size: 0.85rem;
}
</style>
