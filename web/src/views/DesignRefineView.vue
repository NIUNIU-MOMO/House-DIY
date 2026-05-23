<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import { api, type Project } from '@/api/client'

interface RefineDiffItem {
  tag: string
  text: string
  room_id?: string | null
}

interface RefinePreview {
  instruction: string
  diff: RefineDiffItem[]
  patch: Record<string, unknown>
  affected_room_ids: string[]
}

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))

const project = ref<Project | null>(null)
const spec = ref<{ globalStyle: string; rooms: Array<{ id: string; name: string; style: string }> } | null>(null)
const instruction = ref('客厅沙发换更大浅灰布艺，整体更明亮')
const preview = ref<RefinePreview | null>(null)
const submitting = ref(false)
const applying = ref(false)
const error = ref<string | null>(null)

const chips = ['换家具', '改配色', '调灯光', '换材质', '单房间重做']

function appendChip(text: string) {
  if (!instruction.value.includes(text)) {
    instruction.value = `${text}，${instruction.value}`
  }
}

async function loadContext() {
  project.value = await api.getProject(projectId.value)
  spec.value = (await api.getDesignSpec(projectId.value)) as typeof spec.value
}

async function previewRefine() {
  submitting.value = true
  error.value = null
  try {
    preview.value = await api.previewRefine(projectId.value, instruction.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '预览失败'
  } finally {
    submitting.value = false
  }
}

async function applyRefine() {
  if (!preview.value) return
  applying.value = true
  error.value = null
  try {
    await api.applyRefine(projectId.value, {
      patch: preview.value.patch,
      affectedRoomIds: preview.value.affected_room_ids,
    })
    router.push({ name: 'delivery-overview', params: { id: projectId.value } })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '应用失败'
  } finally {
    applying.value = false
  }
}

onMounted(async () => {
  try {
    await loadContext()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  }
})
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="refine-layout">
      <section class="refine-context">
        <div class="page-head">
          <div>
            <h2>方案微调</h2>
            <p class="muted">{{ project?.name }} · DesignSpec 已锁定户型几何</p>
          </div>
          <span class="badge offline">POST /design/refine</span>
        </div>
        <div v-if="spec" class="spec-snapshot">
          <h4>当前方案摘要</h4>
          <p><strong>{{ spec.globalStyle }}</strong></p>
          <ul class="room-spec-list">
            <li v-for="room in spec.rooms" :key="room.id">
              <span>{{ room.name }}</span>
              <em>{{ room.style }}</em>
            </li>
          </ul>
        </div>
      </section>

      <section class="refine-input">
        <h3>描述你想调整的内容</h3>
        <p class="muted tiny">LLM 在现有 DesignSpec 上生成 patch，不修改 FloorPlanModel</p>
        <textarea v-model="instruction" class="input area" rows="5" />
        <div class="chips">
          <button v-for="chip in chips" :key="chip" type="button" class="chip" @click="appendChip(chip)">
            {{ chip }}
          </button>
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="footer-actions">
          <button type="button" class="btn primary" :disabled="submitting" @click="previewRefine">
            {{ submitting ? '解析中…' : '解析并预览变更 →' }}
          </button>
          <button type="button" class="btn ghost" @click="instruction = ''">清空输入</button>
        </div>
      </section>

      <aside class="refine-preview">
        <h4>变更预览（待确认）</h4>
        <ul v-if="preview" class="diff-list">
          <li v-for="(item, index) in preview.diff" :key="index">
            <span class="diff-tag" :class="item.tag">{{ item.tag === 'mod' ? '修改' : '重渲染' }}</span>
            {{ item.text }}
          </li>
        </ul>
        <p v-else class="muted tiny">先输入微调描述并预览</p>
        <button
          type="button"
          class="btn primary block"
          :disabled="!preview || applying"
          @click="applyRefine"
        >
          {{ applying ? '应用中…' : '应用微调并重新生成' }}
        </button>
        <button
          type="button"
          class="btn ghost block"
          @click="router.push({ name: 'delivery-overview', params: { id: projectId } })"
        >
          放弃，保持原方案
        </button>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.refine-layout {
  display: grid;
  grid-template-columns: 1fr 1fr 280px;
  min-height: calc(100vh - 80px);
}

.refine-context,
.refine-input,
.refine-preview {
  padding: 1.25rem;
  border-right: 1px solid #333;
}

.refine-preview {
  background: var(--bg-panel);
  border-right: none;
}

h2 {
  font-family: var(--serif);
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.spec-snapshot {
  background: #2a2824;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 0.85rem;
}

.room-spec-list {
  list-style: none;
  margin-top: 0.5rem;
  font-size: 0.85rem;
}

.room-spec-list li {
  display: flex;
  justify-content: space-between;
  padding: 0.25rem 0;
  color: #ccc;
}

.room-spec-list em {
  color: #888;
  font-style: normal;
}

.area {
  width: 100%;
  resize: vertical;
  margin: 0.75rem 0;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.chip {
  border: 1px solid #444;
  background: var(--bg-panel);
  color: #ddd;
  border-radius: 999px;
  padding: 0.25rem 0.65rem;
  cursor: pointer;
}

.diff-list {
  list-style: none;
  margin-bottom: 1rem;
  font-size: 0.85rem;
}

.diff-list li {
  margin-bottom: 0.5rem;
}

.diff-tag {
  display: inline-block;
  font-size: 0.7rem;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  margin-right: 0.35rem;
  background: #333;
}

.diff-tag.rerender {
  background: #4a3e2c;
  color: #e0c090;
}

.footer-actions {
  display: flex;
  gap: 0.5rem;
}

.btn.block {
  width: 100%;
  margin-bottom: 0.5rem;
}

.error-text {
  color: #d48f8f;
  margin-bottom: 0.75rem;
}

.tiny {
  font-size: 0.75rem;
}
</style>
