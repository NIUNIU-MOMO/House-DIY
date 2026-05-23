<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import ProjectStepBar from '@/components/ProjectStepBar.vue'
import StepBackButton from '@/components/StepBackButton.vue'
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
const parseCompleted = ref(false)

const progress = computed(() => Math.round(task.value?.progress ?? 0))

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

function handleTaskUpdate(next: Task) {
  task.value = next
  if (next.status === 'done') {
    setTimeout(() => {
      router.push({ name: 'floorplan-editor', params: { id: projectId.value } })
    }, 600)
  }
  if (next.status === 'failed') {
    error.value = next.error ?? '解析失败'
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
    <AppHeader active="projects" />
    <div class="ui-page narrow center parse-page">
      <ProjectStepBar :project-id="projectId" current="parse" />
      <StepBackButton :project-id="projectId" current="parse" />

      <div class="loader-card">
        <template v-if="parseCompleted">
          <h2>解析已完成</h2>
          <p class="muted">可前往「校对」查看结果，或重新解析覆盖当前数据</p>
          <div class="revisit-actions">
            <button
              type="button"
              class="btn primary"
              @click="router.push({ name: 'floorplan-editor', params: { id: projectId } })"
            >
              前往校对 →
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
  margin: 0 auto;
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
