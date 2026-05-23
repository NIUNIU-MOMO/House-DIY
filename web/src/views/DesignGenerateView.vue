<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
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
]

function applyPipelineStep(step: string, event: string) {
  pipelineStep.value = step
  const order = ['designSpec', 'render2d', 'scene3d', 'obsidian']
  const idx = order.indexOf(step)
  if (event === 'step_start') {
    order.forEach((key, i) => {
      if (i < idx) stepStatus.value[key] = 'done'
      else if (i === idx) stepStatus.value[key] = 'active'
      else stepStatus.value[key] = 'pending'
    })
  }
  if (event === 'step_done') {
    stepStatus.value[step] = 'done'
  }
  if (event === 'pipeline_done') {
    order.forEach((key) => {
      stepStatus.value[key] = 'done'
    })
  }
}

function handleUpdate(next: Task) {
  task.value = next
  if (next.status === 'done') {
    setTimeout(
      () => router.push({ name: 'delivery-overview', params: { id: projectId.value } }),
      800,
    )
  }
  if (next.status === 'failed') {
    error.value = next.error ?? '生成失败'
  }
}

function handlePipeline(payload: {
  event: string
  pipeline_step: string
  room_index?: number
  room_total?: number
}) {
  applyPipelineStep(payload.pipeline_step, payload.event)
  if (payload.pipeline_step === 'render2d' && payload.room_total) {
    const total = payload.room_total
    renderSlots.value = Array.from({ length: total }, (_, i) => {
      if (payload.event === 'step_done') return 'done'
      if (payload.room_index == null) return 'pending'
      if (i < payload.room_index) return 'done'
      if (i === payload.room_index) return 'active'
      return 'pending'
    })
  }
}

useTaskWebSocket(() => projectId.value, handleUpdate, handlePipeline)

async function poll(currentId: number) {
  const current = await api.getTask(projectId.value, currentId)
  handleUpdate(current)
  if (current.status === 'pending' || current.status === 'running') {
    window.setTimeout(() => poll(currentId), 1000)
  }
}

onMounted(async () => {
  if (!taskId.value) {
    error.value = '缺少 taskId'
    return
  }
  task.value = await api.getTask(projectId.value, taskId.value)
  poll(taskId.value)
})
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="ui-page">
      <h2>正在生成全屋方案</h2>
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
            <p class="tiny muted">{{ task?.step_label || step.desc }}</p>
            <div
              v-if="stepStatus[step.key] === 'active' && step.key === 'render2d'"
              class="mini-progress"
            >
              <div :style="{ width: `${Math.round(task?.progress ?? 0)}%` }" />
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
  margin-top: 0.5rem;
  height: 4px;
  background: #333;
  border-radius: 2px;
  overflow: hidden;
}

.mini-progress > div {
  height: 100%;
  background: var(--accent);
  transition: width 0.3s;
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
