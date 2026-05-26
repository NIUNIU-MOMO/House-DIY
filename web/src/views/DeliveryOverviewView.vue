<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import ProjectStepBar from '@/components/ProjectStepBar.vue'
import StepBackButton from '@/components/StepBackButton.vue'
import { api, type Project, type RenderRecord, type ScenePackage, type SchemeMeta } from '@/api/client'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))

const project = ref<Project | null>(null)
const schemes = ref<SchemeMeta[]>([])
const activeSchemeId = ref<string | null>(null)
const spec = ref<{ globalStyle: string; rooms: Array<{ id: string; name: string }> } | null>(null)
const renders = ref<RenderRecord[]>([])
const scene = ref<ScenePackage | null>(null)
const error = ref<string | null>(null)

async function loadPreview() {
  error.value = null
  try {
    project.value = await api.getProject(projectId.value)
    schemes.value = await api.listSchemes(projectId.value)
    activeSchemeId.value = project.value.active_scheme_id ?? schemes.value[0]?.id ?? null
    if (activeSchemeId.value) {
      try {
        spec.value = (await api.getSchemeSpec(projectId.value, activeSchemeId.value)) as typeof spec.value
      } catch {
        spec.value = null
      }
    }
    renders.value = (await api.listRenders(projectId.value)).rooms
    try {
      scene.value = await api.getScene(projectId.value)
    } catch {
      scene.value = null
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  }
}

watch(activeSchemeId, async (schemeId) => {
  if (!schemeId) {
    spec.value = null
    return
  }
  try {
    spec.value = (await api.getSchemeSpec(projectId.value, schemeId)) as typeof spec.value
  } catch {
    spec.value = null
  }
})

onMounted(loadPreview)
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="ui-page">
      <ProjectStepBar :project-id="projectId" current="preview" />
      <StepBackButton :project-id="projectId" current="preview" />
      <div class="page-head">
        <div>
          <h2>{{ project?.name ?? '项目' }} · 方案预览</h2>
          <p class="muted">{{ spec?.globalStyle ?? '—' }} · 只读预览</p>
        </div>
        <div class="btn-group">
          <select v-model="activeSchemeId" class="input select">
            <option v-for="scheme in schemes" :key="scheme.id" :value="scheme.id">{{ scheme.name }}</option>
          </select>
          <button
            type="button"
            class="btn primary"
            :disabled="!scene"
            @click="router.push({ name: 'scene-viewer', params: { id: projectId } })"
          >
            进入 3D 漫游
          </button>
          <button type="button" class="btn ghost" @click="router.push({ name: 'design-studio', params: { id: projectId } })">
            返回设计编辑
          </button>
        </div>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>

      <h3 v-if="renders.length">2D 效果图</h3>
      <div v-if="renders.length" class="render-grid">
        <article v-for="item in renders" :key="item.room_id" class="render-card">
          <img :src="item.image_url" :alt="item.room_name" />
          <div class="cap">{{ item.room_name }}</div>
        </article>
      </div>
      <p v-else class="muted">当前方案暂无 2D 效果图</p>
    </div>
  </div>
</template>

<style scoped>
h2 {
  font-family: var(--serif);
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.btn-group {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.render-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.render-card {
  background: var(--bg-panel);
  border: 1px solid #333;
  border-radius: var(--radius);
  overflow: hidden;
}

.render-card img {
  width: 100%;
  height: 140px;
  object-fit: cover;
  display: block;
}

.cap {
  padding: 0.5rem 0.75rem;
  font-size: 0.85rem;
}

.error-text {
  color: #d48f8f;
}
</style>
