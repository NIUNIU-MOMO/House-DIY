<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import ProjectStepBar from '@/components/ProjectStepBar.vue'
import StepBackButton from '@/components/StepBackButton.vue'
import { api, type Project, type RenderRecord, type ScenePackage } from '@/api/client'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))

const project = ref<Project | null>(null)
const spec = ref<{ globalStyle: string; rooms: Array<{ id: string; name: string }> } | null>(null)
const renders = ref<RenderRecord[]>([])
const scene = ref<ScenePackage | null>(null)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    project.value = await api.getProject(projectId.value)
    spec.value = (await api.getDesignSpec(projectId.value)) as typeof spec.value
    renders.value = (await api.listRenders(projectId.value)).rooms
    try {
      scene.value = await api.getScene(projectId.value)
    } catch {
      scene.value = null
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  }
})

function renderCountForRoom(roomId: string) {
  return renders.value.some((item) => item.room_id === roomId) ? 1 : 0
}
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="ui-page">
      <ProjectStepBar :project-id="projectId" current="preview" />
      <StepBackButton :project-id="projectId" current="preview" />
      <div class="page-head">
        <div>
          <h2>{{ project?.name ?? '项目' }} · 交付总览</h2>
          <p class="muted">
            {{ spec?.globalStyle ?? '—' }} ·
            {{ project?.status === 'delivered' ? '已交付' : project?.status ?? '—' }}
          </p>
        </div>
        <div class="btn-group">
          <button type="button" class="btn ghost" @click="router.push({ name: 'design-refine', params: { id: projectId } })">
            微调方案
          </button>
          <button type="button" class="btn ghost" @click="router.push({ name: 'design-studio', params: { id: projectId } })">
            重新生成
          </button>
          <button
            type="button"
            class="btn primary"
            :disabled="!scene"
            @click="router.push({ name: 'scene-viewer', params: { id: projectId } })"
          >
            进入 3D 漫游
          </button>
        </div>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>

      <div v-if="spec" class="delivery-grid">
        <section class="panel">
          <h4>房间覆盖</h4>
          <ul class="check-list">
            <li v-for="room in spec.rooms" :key="room.id">
              {{ renderCountForRoom(room.id) ? '✓' : '○' }} {{ room.name }}
              · {{ renderCountForRoom(room.id) }} 张效果图
            </li>
          </ul>
          <p class="tiny muted">Obsidian 案例已自动写入 Vault</p>
        </section>

        <section class="panel">
          <h4>3D 场景</h4>
          <p>{{ scene ? `就绪 · ${scene.rooms.length} 房间 · ${scene.portals?.length ?? 0} 个门洞 Portal` : '未生成' }}</p>
          <button type="button" class="btn sm ghost" @click="router.push({ name: 'render-gallery', params: { id: projectId } })">
            打开 2D 画廊
          </button>
        </section>
      </div>

      <h3 v-if="renders.length">2D 效果图速览</h3>
      <div v-if="renders.length" class="render-grid">
        <button
          v-for="item in renders"
          :key="item.room_id"
          type="button"
          class="render-thumb"
          @click="router.push({ name: 'render-gallery', params: { id: projectId } })"
        >
          <img :src="item.image_url" :alt="item.room_name" />
          <span>{{ item.room_name }}</span>
        </button>
      </div>
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
}

.delivery-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.panel {
  background: var(--bg-panel);
  border: 1px solid #333;
  border-radius: var(--radius);
  padding: 1rem;
}

.panel h4 {
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
}

.check-list {
  list-style: none;
  font-size: 0.85rem;
  line-height: 1.8;
}

.render-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.75rem;
}

.render-thumb {
  border: 1px solid #333;
  border-radius: 8px;
  overflow: hidden;
  background: #2a2824;
  padding: 0;
  cursor: pointer;
  text-align: left;
}

.render-thumb img {
  width: 100%;
  height: 96px;
  object-fit: cover;
  display: block;
}

.render-thumb span {
  display: block;
  padding: 0.35rem 0.5rem;
  font-size: 0.75rem;
  color: #ccc;
}

.error-text {
  color: #d48f8f;
}

.tiny {
  font-size: 0.75rem;
  margin-top: 0.5rem;
}
</style>
