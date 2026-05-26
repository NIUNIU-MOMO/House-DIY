<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import ProjectStepBar from '@/components/ProjectStepBar.vue'
import SchemeList from '@/components/SchemeList.vue'
import StepBackButton from '@/components/StepBackButton.vue'
import { useUnsavedGuard } from '@/composables/useUnsavedGuard'
import { api, type RenderRecord, type SchemeMeta } from '@/api/client'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))

const brief = ref('现代简约、暖白墙面、原木家具、大量自然光')
const refineInstruction = ref('')
const selectedRoomId = ref<string | null>(null)
const schemes = ref<SchemeMeta[]>([])
const activeSchemeId = ref<string | null>(null)
const renders = ref<RenderRecord[]>([])
const existingSpec = ref<{ globalStyle: string; rooms: Array<{ id: string; name: string }> } | null>(null)
const loading = ref(false)
const submitting = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const isDirty = ref(false)

useUnsavedGuard(isDirty)

const activeScheme = computed(() => schemes.value.find((item) => item.id === activeSchemeId.value) ?? null)

watch([brief, refineInstruction], () => {
  isDirty.value = true
})

async function loadSchemes() {
  loading.value = true
  error.value = null
  try {
    schemes.value = await api.listSchemes(projectId.value)
    if (!activeSchemeId.value && schemes.value.length) {
      activeSchemeId.value = schemes.value[0]?.id ?? null
    }
    await loadSchemeDetail()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载方案失败'
  } finally {
    loading.value = false
  }
}

async function loadSchemeDetail() {
  if (!activeSchemeId.value) {
    existingSpec.value = null
    renders.value = []
    return
  }
  try {
    existingSpec.value = (await api.getSchemeSpec(projectId.value, activeSchemeId.value)) as typeof existingSpec.value
  } catch {
    existingSpec.value = null
  }
  try {
    renders.value = (await api.listRenders(projectId.value)).rooms
  } catch {
    renders.value = []
  }
}

async function onSelectScheme(schemeId: string) {
  activeSchemeId.value = schemeId
  isDirty.value = false
  await loadSchemeDetail()
}

async function generate2d() {
  if (!activeSchemeId.value) {
    return
  }
  submitting.value = true
  error.value = null
  try {
    const task = await api.generateScheme2d(projectId.value, activeSchemeId.value, {
      brief: brief.value,
      globalStyle: '现代简约',
      useRag: true,
    })
    isDirty.value = false
    router.push({
      name: 'design-generate',
      params: { id: projectId.value },
      query: { taskId: task.id, schemeId: activeSchemeId.value },
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '生成 2D 失败'
  } finally {
    submitting.value = false
  }
}

async function saveScheme() {
  if (!activeSchemeId.value || !existingSpec.value) {
    error.value = '请先生成 2D 并确认 DesignSpec'
    return
  }
  saving.value = true
  error.value = null
  try {
    await api.saveSchemeSpec(projectId.value, activeSchemeId.value, existingSpec.value as Record<string, unknown>)
    isDirty.value = false
    await loadSchemes()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存方案失败'
  } finally {
    saving.value = false
  }
}

async function generate3d() {
  if (!activeSchemeId.value) {
    return
  }
  submitting.value = true
  error.value = null
  try {
    await api.generateScheme3d(projectId.value, activeSchemeId.value)
    isDirty.value = false
    await loadSchemes()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '生成 3D 失败'
  } finally {
    submitting.value = false
  }
}

async function applyRefine() {
  if (!activeSchemeId.value || !refineInstruction.value.trim()) {
    return
  }
  submitting.value = true
  error.value = null
  try {
    const preview = await api.previewRefine(
      projectId.value,
      refineInstruction.value,
      activeSchemeId.value,
    )
    await api.applyRefine(projectId.value, {
      patch: preview.patch,
      affectedRoomIds: selectedRoomId.value ? [selectedRoomId.value] : preview.affected_room_ids,
      schemeId: activeSchemeId.value,
    })
    refineInstruction.value = ''
    isDirty.value = false
    await loadSchemeDetail()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '微调失败'
  } finally {
    submitting.value = false
  }
}

onMounted(loadSchemes)
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="design-workspace">
      <SchemeList
        :project-id="projectId"
        :schemes="schemes"
        :active-scheme-id="activeSchemeId"
        :loading="loading"
        @select="onSelectScheme"
        @created="(s) => { schemes.push(s); activeSchemeId = s.id; loadSchemeDetail() }"
        @deleted="(id) => { schemes = schemes.filter((s) => s.id !== id); activeSchemeId = schemes[0]?.id ?? null; loadSchemeDetail() }"
      />
      <section class="design-content">
        <ProjectStepBar :project-id="projectId" current="design" />
        <StepBackButton :project-id="projectId" current="design" />
        <h2>描述你的理想之家</h2>
        <div v-if="activeScheme" class="spec-banner">
          {{ activeScheme.name }} · {{ activeScheme.status }}
          <span v-if="activeScheme.stale"> · 标注已变更，需更新</span>
        </div>
        <textarea v-model="brief" class="input light area" rows="5" />
        <div class="action-row">
          <button type="button" class="btn primary" :disabled="submitting || !activeSchemeId" @click="generate2d">
            {{ submitting ? '提交中…' : '生成 2D' }}
          </button>
          <button type="button" class="btn" :disabled="saving || !existingSpec" @click="saveScheme">
            {{ saving ? '保存中…' : '保存方案' }}
          </button>
          <button type="button" class="btn ghost" :disabled="submitting || !activeSchemeId" @click="generate3d">
            生成 3D 漫游
          </button>
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div v-if="existingSpec?.rooms?.length" class="room-thumbs">
          <button
            v-for="room in existingSpec.rooms"
            :key="room.id"
            type="button"
            class="room-thumb"
            :class="{ selected: selectedRoomId === room.id }"
            @click="selectedRoomId = selectedRoomId === room.id ? null : room.id"
          >
            {{ room.name }}
          </button>
        </div>
        <div class="refine-row">
          <input
            v-model="refineInstruction"
            class="input light"
            :placeholder="selectedRoomId ? '描述选中房间的调整…' : '描述全屋调整（未选房间则全部生效）'"
          />
          <button type="button" class="btn sm primary" :disabled="submitting" @click="applyRefine">应用</button>
        </div>
        <div v-if="renders.length" class="render-preview">
          <h4>2D 预览</h4>
          <div class="render-grid">
            <figure v-for="item in renders" :key="item.room_id">
              <img :src="item.image_url" :alt="item.room_name" />
              <figcaption>{{ item.room_name }}</figcaption>
            </figure>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.design-workspace {
  display: grid;
  grid-template-columns: 180px 1fr;
  min-height: calc(100vh - 80px);
}

.design-content {
  padding: 1.5rem;
}

.design-content h2 {
  font-family: var(--serif);
  margin-bottom: 0.75rem;
}

.spec-banner {
  background: #2c4a3e;
  color: #8fd4a8;
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  font-size: 0.85rem;
  margin-bottom: 0.75rem;
}

.area {
  width: 100%;
  resize: vertical;
  margin-bottom: 0.75rem;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.room-thumbs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 1rem 0;
}

.room-thumb {
  border: 2px solid #444;
  background: #2a2824;
  color: #ccc;
  border-radius: 6px;
  padding: 0.35rem 0.65rem;
  font-size: 0.78rem;
  cursor: pointer;
}

.room-thumb.selected {
  border-color: var(--accent);
  color: #fff;
}

.refine-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.refine-row .input {
  flex: 1;
}

.render-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 0.5rem;
}

.render-grid img {
  width: 100%;
  height: 80px;
  object-fit: cover;
  border-radius: 6px;
}

.render-grid figcaption {
  font-size: 0.72rem;
  color: #aaa;
  margin-top: 0.25rem;
}

.error-text {
  color: #d48f8f;
  margin-bottom: 0.75rem;
}
</style>
