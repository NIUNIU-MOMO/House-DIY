<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import FloorPlanEditor from '@/components/FloorPlanEditor/index.vue'

const route = useRoute()
const projectId = computed(() => Number(route.params.id))
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="steps editor-steps">
      <span class="done">1 上传</span>
      <span class="done">2 解析</span>
      <span class="active">3 校对</span>
      <span>4 设计</span>
    </div>
    <FloorPlanEditor :project-id="projectId" />
  </div>
</template>

<style scoped>
.editor-steps {
  padding: 1rem 1.5rem 0;
  max-width: none;
}
</style>
