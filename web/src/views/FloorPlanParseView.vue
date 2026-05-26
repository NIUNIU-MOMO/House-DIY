<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import ProjectStepBar from '@/components/ProjectStepBar.vue'
import { api, type Task } from '@/api/client'
import { useTaskWebSocket } from '@/composables/useTaskWebSocket'
import { PARSE_STEP_LABELS } from '@/types/task'
import { resolveMaxCompletedStepIndex, stepIndex } from '@/utils/projectNavigation'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))

const task = ref<Task | null>(null)
const error = ref<string | null>(null)
const starting = ref(false)
const cancelling = ref(false)
const parseCompleted = ref(false)
const logPanelRef = ref<HTMLElement | null>(null)

const progress = computed(() => Math.round(task.value?.progress ?? 0))
const isParseActive = computed(
  () => task.value?.status === 'pending' || task.value?.status === 'running',
)
const taskLogs = computed(() => task.value?.logs ?? [])

function stepClass(index: number) {
  if (!task.value) {
    return index === 0 ? 'active' : ''
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

function handleTaskUpdate(next: Task) {
  task.value = next
  scrollLogsToBottom()
  if (next.status === 'done') {
    setTimeout(() => {
      router.push({ name: 'floorplan-editor', params: { id: projectId.value } })
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
  parseCompleted.value = false
  try {
    const created = await api.startFloorplanParse(projectId.value)
    task.value = created
    pollTask(created.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '无法启动解析'
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
  if (maxIdx > stepIndex('parse')) {
    parseCompleted.value = true
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
      </div>

      <div class="loader-card">
        <template v-if="parseCompleted">
          <h2>解析已完成</h2>
          <p class="muted">可前往「标注」查看结果，或重新解析覆盖当前数据</p>
          <div class="revisit-actions">
            <button
              type="button"
              class="btn primary"
              @click="router.push({ name: 'floorplan-editor', params: { id: projectId } })"
            >
              前往标注 →
            </button>
            <button type="button" class="btn ghost" :disabled="starting" @click="startParse">
              重新解析
            </button>
          </div>
        </template>
        <template v-else>
          <div class="spinner" />
          <h2>{{ task?.status === 'failed' ? '解析失败' : '正在解析户型…' }}</h2>
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
        </template>
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

.revisit-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  justify-content: center;
  margin-top: 1rem;
}
</style>
