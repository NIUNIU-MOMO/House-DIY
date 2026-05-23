<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import ProjectStepBar from '@/components/ProjectStepBar.vue'
import StepBackButton from '@/components/StepBackButton.vue'
import { api, type Task } from '@/api/client'
import { useTaskWebSocket } from '@/composables/useTaskWebSocket'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))
const taskId = computed(() => Number(route.query.taskId))

const task = ref<Task | null>(null)
const error = ref<string | null>(null)
const pipelineStep = ref<string>('designSpec')
const stepStatus = ref<Record<string, 'pending' | 'active' | 'done'>>({
  designSpec: 'pending',
  render2d: 'pending',
  scene3d: 'pending',
  obsidian: 'pending',
})
const renderSlots = ref<Array<'pending' | 'active' | 'done'>>([])

const steps = [
  { key: 'designSpec', title: 'DesignSpec', desc: 'LLM 生成全屋设计规格' },
  { key: 'render2d', title: '2D 效果图', desc: 'ComfyUI 逐房间渲染' },
  { key: 'scene3d', title: '3D 场景构建', desc: 'Scene Builder 全屋场景' },
  { key: 'obsidian', title: 'Obsidian 案例', desc: '写入 Vault 案例笔记' },
] as const

type StepKey = (typeof steps)[number]['key']

const STEP_ORDER: StepKey[] = ['designSpec', 'render2d', 'scene3d', 'obsidian']

/** 与 orchestrator 总进度区间对齐 */
const STEP_RANGES: Record<StepKey, { start: number; end: number }> = {
  designSpec: { start: 5, end: 25 },
  render2d: { start: 30, end: 72 },
  scene3d: { start: 75, end: 85 },
  obsidian: { start: 88, end: 95 },
}

const renderRoomProgress = ref({ index: 0, total: 0 })
const roomRendering = ref(false)

function syncStepStatusFromTask(next: Task) {
  if (next.status === 'done') {
    STEP_ORDER.forEach((key) => {
      stepStatus.value[key] = 'done'
    })
    return
  }
  const activeIndex = Math.min(Math.max(next.step, 0), STEP_ORDER.length - 1)
  STEP_ORDER.forEach((key, index) => {
    if (index < activeIndex) {
      stepStatus.value[key] = 'done'
    } else if (index === activeIndex) {
      stepStatus.value[key] = 'active'
    } else {
      stepStatus.value[key] = 'pending'
    }
  })
}

function stepProgressPercent(key: StepKey): number {
  const status = stepStatus.value[key]
  if (status === 'pending') {
    return 0
  }
  if (status === 'done') {
    return 100
  }

  const overall = task.value?.progress ?? 0
  const range = STEP_RANGES[key]
  if (overall <= range.start) {
    return 0
  }
  if (overall >= range.end) {
    return 100
  }
  return Math.round(((overall - range.start) / (range.end - range.start)) * 100)
}

function stepDetailLabel(key: StepKey, desc: string): string {
  const status = stepStatus.value[key]
  if (status !== 'active') {
    return desc
  }
  if (key === 'render2d' && renderRoomProgress.value.total > 0) {
    const { index, total } = renderRoomProgress.value
    const roomLabel = task.value?.step_label?.replace(/^渲染\s*/, '') ?? ''
    const namePart = roomLabel ? ` · ${roomLabel}` : ''
    if (roomRendering.value && stepProgressPercent(key) < 100) {
      return `ComfyUI 渲染中 (${index + 1}/${total})${namePart} · Flux 单张约 3–10 分钟`
    }
    return `渲染中 (${index + 1}/${total})${namePart}`
  }
  return task.value?.step_label || desc
}

function applyPipelineStep(step: string, event: string) {
  pipelineStep.value = step
  const idx = STEP_ORDER.indexOf(step as StepKey)
  if (event === 'step_start') {
    STEP_ORDER.forEach((key, i) => {
      if (i < idx) stepStatus.value[key] = 'done'
      else if (i === idx) stepStatus.value[key] = 'active'
      else stepStatus.value[key] = 'pending'
    })
  }
  if (event === 'step_done') {
    stepStatus.value[step as StepKey] = 'done'
  }
  if (event === 'pipeline_done') {
    STEP_ORDER.forEach((key) => {
      stepStatus.value[key] = 'done'
    })
  }
}

function handleUpdate(next: Task) {
  task.value = next
  syncStepStatusFromTask(next)
  if (next.status === 'done') {
    roomRendering.value = false
    setTimeout(
      () => router.push({ name: 'delivery-overview', params: { id: projectId.value } }),
      800,
    )
  }
  if (next.error && (next.status === 'failed' || next.status === 'pending')) {
    error.value = next.error
    roomRendering.value = false
  } else if (next.status === 'failed') {
    error.value = next.error ?? '生成失败'
    roomRendering.value = false
  } else if (next.status === 'running') {
    error.value = null
  }
}

function applyRenderRoom(payload: {
  room_index?: number
  room_total?: number
  room_name?: string
}) {
  if (!payload.room_total) {
    return
  }
  renderRoomProgress.value = {
    index: payload.room_index ?? 0,
    total: payload.room_total,
  }
  renderSlots.value = Array.from({ length: payload.room_total }, (_, i) => {
    const current = payload.room_index ?? 0
    if (i < current) return 'done'
    if (i === current) return 'active'
    return 'pending'
  })
}

function handlePipeline(payload: {
  event: string
  pipeline_step: string
  room_index?: number
  room_total?: number
  room_name?: string
}) {
  applyPipelineStep(payload.pipeline_step, payload.event)
  if (payload.pipeline_step === 'render2d') {
    if (payload.event === 'room_start' || payload.event === 'room_poll') {
      roomRendering.value = true
      applyRenderRoom(payload)
    }
    if (payload.event === 'step_progress' || payload.event === 'room_start') {
      applyRenderRoom(payload)
    }
    if (payload.event === 'step_done') {
      roomRendering.value = false
    }
  }
}

function retryGenerate() {
  router.push({ name: 'design-studio', params: { id: projectId.value } })
}

useTaskWebSocket(() => projectId.value, handleUpdate, handlePipeline)

async function poll(currentId: number) {
  const current = await api.getTask(projectId.value, currentId)
  handleUpdate(current)
  if ((current.status === 'pending' || current.status === 'running') && !current.error) {
    window.setTimeout(() => poll(currentId), 1000)
  }
}

onMounted(async () => {
  if (!taskId.value) {
    error.value = '缺少 taskId'
    return
  }
  const initial = await api.getTask(projectId.value, taskId.value)
  handleUpdate(initial)
  if (initial.step === 1 && initial.status === 'running') {
    roomRendering.value = true
    try {
      const spec = (await api.getDesignSpec(projectId.value)) as { rooms: unknown[] }
      renderRoomProgress.value = { index: 0, total: spec.rooms.length }
      applyRenderRoom({ room_index: 0, room_total: spec.rooms.length })
    } catch {
      // ignore
    }
  }
  poll(taskId.value)
})
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="ui-page">
      <ProjectStepBar :project-id="projectId" current="design" />
      <StepBackButton :project-id="projectId" current="design" />
      <h2>{{ error ? '生成失败' : '正在生成全屋方案' }}</h2>
      <p class="muted">GPU 队列串行 · 请勿关闭 oMLX / ComfyUI</p>

      <div class="pipeline">
        <div
          v-for="step in steps"
          :key="step.key"
          class="pipe-step"
          :class="stepStatus[step.key]"
        >
          <span class="icon">
            {{ stepStatus[step.key] === 'done' ? '✓' : stepStatus[step.key] === 'active' ? '◐' : '○' }}
          </span>
          <div>
            <strong>{{ step.title }}</strong>
            <p class="tiny muted">{{ stepDetailLabel(step.key, step.desc) }}</p>
            <div v-if="stepStatus[step.key] !== 'pending'" class="step-progress">
              <div
                class="mini-progress"
                :class="{ indeterminate: step.key === 'render2d' && roomRendering && stepProgressPercent(step.key) <= 5 }"
              >
                <div :style="{ width: `${Math.max(stepProgressPercent(step.key), roomRendering && step.key === 'render2d' ? 8 : 0)}%` }" />
              </div>
              <span class="step-pct">
                {{ step.key === 'render2d' && roomRendering && stepProgressPercent(step.key) <= 5 ? '…' : `${stepProgressPercent(step.key)}%` }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="renderSlots.length" class="live-preview">
        <div
          v-for="(slot, index) in renderSlots"
          :key="index"
          class="render-slot"
          :class="slot"
        >
          <span>房间 {{ index + 1 }}{{ slot === 'active' ? '…' : '' }}</span>
        </div>
      </div>

      <p class="muted progress-text">{{ Math.round(task?.progress ?? 0) }}%</p>
      <p v-if="error" class="error-text">{{ error }}</p>
      <button v-if="error" type="button" class="btn primary" @click="retryGenerate">
        返回设计页重试
      </button>
    </div>
  </div>
</template>

<style scoped>
h2 {
  font-family: var(--serif);
}

.pipeline {
  margin-top: 1.25rem;
  display: grid;
  gap: 0.75rem;
}

.pipe-step {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  background: var(--bg-panel);
  border: 1px solid #333;
  border-radius: var(--radius);
  padding: 0.85rem 1rem;
}

.pipe-step.active {
  border-color: var(--accent);
}

.pipe-step.done {
  border-color: #3a4a3e;
}

.pipe-step .icon {
  font-size: 1.1rem;
  width: 1.5rem;
  text-align: center;
  color: #888;
}

.pipe-step.active .icon {
  color: var(--accent);
}

.pipe-step.done .icon {
  color: #8fd4a8;
}

.mini-progress {
  flex: 1;
  height: 4px;
  background: #333;
  border-radius: 2px;
  overflow: hidden;
}

.step-progress {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.step-pct {
  font-size: 0.72rem;
  color: #888;
  min-width: 2.25rem;
  text-align: right;
}

.pipe-step.active .step-pct {
  color: var(--accent);
}

.pipe-step.done .step-pct {
  color: #8fd4a8;
}

.mini-progress > div {
  height: 100%;
  background: var(--accent);
  transition: width 0.3s;
}

.mini-progress.indeterminate > div {
  animation: render-pulse 1.6s ease-in-out infinite;
}

@keyframes render-pulse {
  0%,
  100% {
    opacity: 0.45;
  }
  50% {
    opacity: 1;
  }
}

.live-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1.25rem;
}

.render-slot {
  width: 88px;
  height: 64px;
  border-radius: 8px;
  background: #2a2824;
  border: 1px solid #333;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  color: #888;
}

.render-slot.active {
  border-color: var(--accent);
  color: var(--accent);
}

.render-slot.done {
  border-color: #3a4a3e;
  color: #8fd4a8;
}

.progress-text {
  margin-top: 1rem;
  text-align: center;
}

.error-text {
  color: #d48f8f;
  margin-top: 1rem;
}

.tiny {
  font-size: 0.75rem;
}
</style>
