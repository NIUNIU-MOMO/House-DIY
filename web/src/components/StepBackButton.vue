<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { previousStep, stepToRouteName, type ProjectStep } from '@/utils/projectNavigation'

const props = defineProps<{
  projectId: number
  current: ProjectStep
}>()

const router = useRouter()

const prev = computed(() => previousStep(props.current))

const label = computed(() => {
  const labels: Record<ProjectStep, string> = {
    upload: '',
    parse: '← 返回上传',
    review: '← 返回解析',
    design: '← 返回校对',
    preview: '← 返回设计',
  }
  return labels[props.current]
})

function goBack() {
  const step = prev.value
  if (!step) {
    return
  }
  router.push({ name: stepToRouteName(step), params: { id: props.projectId } })
}
</script>

<template>
  <button v-if="prev" type="button" class="btn ghost sm step-back" @click="goBack">
    {{ label }}
  </button>
</template>

<style scoped>
.step-back {
  margin-bottom: 0.75rem;
}
</style>
