<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import ProjectStepBar from '@/components/ProjectStepBar.vue'
import StepBackButton from '@/components/StepBackButton.vue'
import FloorPlanEditor from '@/components/FloorPlanEditor/index.vue'
import { useUnsavedGuard } from '@/composables/useUnsavedGuard'

const route = useRoute()
const projectId = computed(() => Number(route.params.id))

const isDirty = ref(false)
useUnsavedGuard(isDirty)
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="editor-head">
      <ProjectStepBar :project-id="projectId" current="annotate" />
      <StepBackButton :project-id="projectId" current="annotate" />
    </div>
    <FloorPlanEditor v-model:dirty="isDirty" :project-id="projectId" />
  </div>
</template>

<style scoped>
.editor-head {
  padding: 1rem 1.5rem 0;
}
</style>
