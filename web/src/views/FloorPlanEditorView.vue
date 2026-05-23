<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import ProjectStepBar from '@/components/ProjectStepBar.vue'
import StepBackButton from '@/components/StepBackButton.vue'
import FloorPlanEditor from '@/components/FloorPlanEditor/index.vue'

const route = useRoute()
const projectId = computed(() => Number(route.params.id))
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="editor-head">
      <ProjectStepBar :project-id="projectId" current="review" />
      <StepBackButton :project-id="projectId" current="review" />
    </div>
    <FloorPlanEditor :project-id="projectId" />
  </div>
</template>

<style scoped>
.editor-head {
  padding: 1rem 1.5rem 0;
}
</style>
