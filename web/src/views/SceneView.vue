<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import SceneViewer3D from '@/components/SceneViewer3D/index.vue'
import { api, type ScenePackage } from '@/api/client'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))

const scene = ref<ScenePackage | null>(null)
const activeRoomId = ref<string | null>(null)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    scene.value = await api.getScene(projectId.value)
    activeRoomId.value = scene.value.active_room ?? scene.value.rooms[0]?.id ?? null
  } catch (e) {
    error.value = e instanceof Error ? e.message : '3D 场景未就绪'
  }
})
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="scene-toolbar">
      <button type="button" class="btn sm ghost" @click="router.push({ name: 'delivery-overview', params: { id: projectId } })">
        ← 返回总览
      </button>
      <span v-if="scene" class="muted">3D 漫游 · {{ scene.rooms.length }} 个房间</span>
    </div>

    <p v-if="error" class="error-text ui-page">{{ error }}</p>

    <SceneViewer3D
      v-if="scene && activeRoomId"
      :gltf-url="scene.gltf_url"
      :model-file="scene.gltf"
      :rooms="scene.rooms"
      :active-room-id="activeRoomId"
      @room-change="activeRoomId = $event"
    />
  </div>
</template>

<style scoped>
.scene-toolbar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid #333;
  background: var(--bg-panel);
}

.error-text {
  color: #d48f8f;
  padding: 1.5rem;
}
</style>
