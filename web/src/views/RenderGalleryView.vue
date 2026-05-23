<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import { api, type RenderRecord } from '@/api/client'

const route = useRoute()
const projectId = computed(() => Number(route.params.id))

const renders = ref<RenderRecord[]>([])
const activeRoomId = ref<string | null>(null)
const regenerating = ref(false)
const error = ref<string | null>(null)

const activeRender = computed(() =>
  renders.value.find((item) => item.room_id === activeRoomId.value) ?? renders.value[0] ?? null,
)

async function loadRenders() {
  error.value = null
  try {
    const manifest = await api.listRenders(projectId.value)
    renders.value = manifest.rooms
    if (!activeRoomId.value && manifest.rooms.length > 0) {
      activeRoomId.value = manifest.rooms[0]!.room_id
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  }
}

async function regenerateRoom() {
  if (!activeRender.value) return
  regenerating.value = true
  error.value = null
  try {
    await api.regenerateRender(projectId.value, activeRender.value.room_id)
    window.setTimeout(loadRenders, 2000)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '重生成失败'
  } finally {
    regenerating.value = false
  }
}

function downloadImage() {
  if (!activeRender.value) return
  const link = document.createElement('a')
  link.href = activeRender.value.image_url
  link.download = activeRender.value.filename
  link.click()
}

onMounted(loadRenders)
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="ui-page">
      <h2>2D 效果图画廊</h2>
      <div class="head-actions">
        <button type="button" class="btn sm primary" @click="$router.push({ name: 'scene-viewer', params: { id: projectId } })">
          进入 3D 漫游 →
        </button>
      </div>
      <p v-if="error" class="error-text">{{ error }}</p>
      <p v-if="!renders.length && !error" class="muted">暂无渲染图，请先生成全屋方案</p>

      <div v-if="renders.length" class="gallery-layout">
        <aside class="room-nav">
          <button
            v-for="item in renders"
            :key="item.room_id"
            type="button"
            :class="{ active: item.room_id === activeRoomId }"
            @click="activeRoomId = item.room_id"
          >
            {{ item.room_name }}
          </button>
        </aside>

        <section class="gallery-main">
          <div v-if="activeRender" class="big-render">
            <img :src="activeRender.image_url" :alt="activeRender.room_name" />
            <span class="render-label">{{ activeRender.room_name }}</span>
          </div>

          <div class="thumb-row">
            <button
              v-for="item in renders"
              :key="item.room_id"
              type="button"
              class="thumb"
              :class="{ active: item.room_id === activeRoomId }"
              @click="activeRoomId = item.room_id"
            >
              <img :src="item.image_url" :alt="item.room_name" />
            </button>
          </div>

          <div class="meta-bar">
            <span>ComfyUI · {{ activeRender?.workflow }}</span>
            <button type="button" class="btn sm ghost" :disabled="regenerating" @click="regenerateRoom">
              {{ regenerating ? '入队中…' : '仅重生成此房间' }}
            </button>
            <button type="button" class="btn sm ghost" @click="downloadImage">下载</button>
          </div>

          <details v-if="activeRender" class="prompt-details" open>
            <summary>查看 Prompt / DesignSpec 片段</summary>
            <pre>{{ activeRender.prompt }}</pre>
            <p v-if="activeRender.negative" class="tiny muted">Negative: {{ activeRender.negative }}</p>
          </details>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
h2 {
  font-family: var(--serif);
}

.head-actions {
  margin-top: 0.75rem;
}

.gallery-layout {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: 1.25rem;
  margin-top: 1.25rem;
}

.room-nav {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.room-nav button {
  text-align: left;
  padding: 0.55rem 0.75rem;
  border: 1px solid #333;
  border-radius: 8px;
  background: var(--bg-panel);
  color: #ccc;
  cursor: pointer;
}

.room-nav button.active {
  border-color: var(--accent);
  color: var(--accent);
}

.big-render {
  position: relative;
  background: #2a2824;
  border: 1px solid #333;
  border-radius: var(--radius);
  min-height: 360px;
  overflow: hidden;
}

.big-render img {
  width: 100%;
  display: block;
  object-fit: contain;
  max-height: 480px;
}

.render-label {
  position: absolute;
  top: 0.75rem;
  left: 0.75rem;
  background: rgba(0, 0, 0, 0.55);
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  font-size: 0.85rem;
}

.thumb-row {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
  overflow-x: auto;
}

.thumb {
  width: 72px;
  height: 54px;
  border: 2px solid #333;
  border-radius: 6px;
  padding: 0;
  overflow: hidden;
  cursor: pointer;
  background: #2a2824;
  flex-shrink: 0;
}

.thumb.active {
  border-color: var(--accent);
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.meta-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.85rem;
  font-size: 0.85rem;
  color: #aaa;
}

.prompt-details {
  margin-top: 1rem;
  background: var(--bg-panel);
  border: 1px solid #333;
  border-radius: 8px;
  padding: 0.75rem 1rem;
}

.prompt-details pre {
  white-space: pre-wrap;
  font-size: 0.8rem;
  color: #ccc;
  margin-top: 0.5rem;
}

.error-text {
  color: #d48f8f;
}

.tiny {
  font-size: 0.75rem;
}
</style>
