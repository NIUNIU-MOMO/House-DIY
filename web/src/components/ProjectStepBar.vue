<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

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
}>()

const router = useRouter()
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
  return ''
}

function canGoTo(key: ProjectStep) {
  return isStepReachable(key, maxCompletedIndex.value)
}

function goToStep(key: ProjectStep) {
  if (!canGoTo(key)) {
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
  background: var(--accent-2);
  color: #fff;
  cursor: pointer;
}

.step-chip.active:hover {
  filter: brightness(1.05);
}

.step-chip:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
