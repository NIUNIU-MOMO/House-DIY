<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useUnsavedGuardConsumer } from '@/composables/useUnsavedGuard'
import {
  PROJECT_STEPS,
  isStepReachable,
  resolveMaxCompletedStepIndex,
  stepIndex,
  type ProjectStep,
} from '@/utils/projectNavigation'

const props = defineProps<{
  projectId: number
  current: ProjectStep
  locked?: boolean
  /** 禁止从流程条进入的步骤（如解析回访页不可直跳标注） */
  blockedSteps?: ProjectStep[]
}>()

const router = useRouter()
const confirmLeave = useUnsavedGuardConsumer()
const maxCompletedIndex = ref(stepIndex(props.current))

async function loadProgress() {
  maxCompletedIndex.value = await resolveMaxCompletedStepIndex(props.projectId)
}

function stepClass(key: ProjectStep) {
  if (key === props.current) {
    return 'active'
  }
  if (isStepReachable(key, maxCompletedIndex.value)) {
    return 'done'
  }
  return 'pending'
}

function canGoTo(key: ProjectStep) {
  if (props.locked) {
    return false
  }
  if (props.blockedSteps?.includes(key)) {
    return false
  }
  return isStepReachable(key, maxCompletedIndex.value)
}

async function goToStep(key: ProjectStep) {
  if (!canGoTo(key) || key === props.current) {
    return
  }
  if (!(await confirmLeave())) {
    return
  }
  const step = PROJECT_STEPS[stepIndex(key)]
  if (!step) {
    return
  }
  router.push({ name: step.route, params: { id: props.projectId } })
}

onMounted(loadProgress)
watch(() => props.projectId, loadProgress)
</script>

<template>
  <nav class="steps project-steps" aria-label="项目流程">
    <button
      v-for="step in PROJECT_STEPS"
      :key="step.key"
      type="button"
      class="step-chip"
      :class="stepClass(step.key)"
      :disabled="!canGoTo(step.key)"
      @click="goToStep(step.key)"
    >
      {{ step.label }}
    </button>
  </nav>
</template>

<style scoped>
.project-steps {
  margin-bottom: 1.5rem;
}

.step-chip {
  border: none;
  padding: 0.25rem 0.6rem;
  border-radius: 20px;
  background: #333;
  color: #888;
  font-size: 0.78rem;
  cursor: default;
}

.step-chip.done {
  background: #2c4a3e;
  color: #8fd4a8;
  cursor: pointer;
}

.step-chip.done:hover {
  filter: brightness(1.08);
}

.step-chip.active {
  background: #5c4a1e;
  color: #f0c14b;
  font-weight: 600;
  cursor: pointer;
}

.step-chip.active:hover {
  filter: brightness(1.05);
}

.step-chip.pending {
  opacity: 0.65;
}

.step-chip:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
