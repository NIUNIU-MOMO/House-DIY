<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import { api } from '@/api/client'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))

const brief = ref('现代简约、暖白墙面、原木家具、大量自然光')
const globalStyle = ref('现代简约')
const useRag = ref(true)
const submitting = ref(false)
const error = ref<string | null>(null)

const styleChips = ['现代简约', '北欧', '新中式', '轻奢', '奶油风']

interface RagCase {
  id: string
  title: string
  score: number
  desc?: string
}

const ragCases = ref<RagCase[]>([])
const existingSpec = ref<{ globalStyle: string; rooms: Array<{ name: string }> } | null>(null)

function appendChip(chip: string) {
  globalStyle.value = chip
  if (!brief.value.includes(chip)) {
    brief.value = `${chip}，${brief.value}`
  }
}

async function loadRag() {
  try {
    existingSpec.value = (await api.getDesignSpec(projectId.value)) as {
      globalStyle: string
      rooms: Array<{ name: string }>
    }
  } catch {
    existingSpec.value = null
  }
  const resp = await api.searchKnowledge(brief.value)
  ragCases.value = resp.results.map((item) => ({
    id: item.id,
    title: item.title,
    score: item.score,
    desc: item.desc || 'Obsidian RAG 检索',
  }))
}

async function startGeneration() {
  submitting.value = true
  error.value = null
  try {
    const task = await api.generateDesign(projectId.value, {
      brief: brief.value,
      globalStyle: globalStyle.value,
      useRag: useRag.value,
    })
    router.push({ name: 'design-generate', params: { id: projectId.value }, query: { taskId: task.id } })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '启动失败'
  } finally {
    submitting.value = false
  }
}

onMounted(loadRag)
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="design-layout">
      <section class="design-main">
        <div class="steps inline">
          <span class="done">户型已确认</span>
          <span class="active">描述需求</span>
          <span>生成</span>
        </div>
        <h2>描述你的理想之家</h2>
        <div v-if="existingSpec" class="spec-banner">
          已有 DesignSpec：{{ existingSpec.globalStyle }} · {{ existingSpec.rooms.length }} 个房间
        </div>
        <textarea v-model="brief" class="input light area" rows="6" />
        <div class="chips">
          <button
            v-for="chip in styleChips"
            :key="chip"
            type="button"
            class="chip"
            @click="appendChip(chip)"
          >
            {{ chip }}
          </button>
        </div>
        <div class="option-row">
          <label><input v-model="useRag" type="checkbox" /> 参考历史案例 (RAG)</label>
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
        <button type="button" class="btn primary lg" :disabled="submitting" @click="startGeneration">
          {{ submitting ? '提交中…' : '生成全屋方案 →' }}
        </button>
      </section>

      <aside class="rag-panel">
        <h4>相似案例（Obsidian RAG）</h4>
        <article v-for="item in ragCases" :key="item.id" class="rag-card">
          <strong>{{ item.title }}</strong>
          <p class="tiny muted">{{ item.desc }}</p>
          <span class="score">相似度 {{ item.score }}</span>
        </article>
        <p class="tiny muted">将使用 oMLX → DesignSpec · ComfyUI 2D · Scene Builder 3D</p>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.design-layout {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 0;
  min-height: calc(100vh - 80px);
}

.design-main {
  padding: 1.5rem;
}

.design-main h2 {
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

.option-row {
  margin-bottom: 1rem;
  font-size: 0.85rem;
  color: #aaa;
}

.btn.lg {
  padding: 0.75rem 1.25rem;
  font-size: 1rem;
}

.rag-panel {
  background: var(--bg-panel);
  border-left: 1px solid #333;
  padding: 1.25rem;
}

.rag-panel h4 {
  font-size: 0.85rem;
  margin-bottom: 0.75rem;
}

.rag-card {
  background: #2a2824;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 0.75rem;
  margin-bottom: 0.65rem;
}

.rag-card strong {
  display: block;
  font-size: 0.85rem;
  margin-bottom: 0.25rem;
}

.score {
  font-size: 0.72rem;
  color: #8fd4a8;
}

.error-text {
  color: #d48f8f;
  margin-bottom: 0.75rem;
}

.tiny {
  font-size: 0.75rem;
}
</style>
