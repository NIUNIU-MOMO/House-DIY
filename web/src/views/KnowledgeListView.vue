<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import { api, type KnowledgeDocument } from '@/api/client'

const router = useRouter()
const tab = ref<'all' | 'case' | 'ref' | 'preset'>('all')
const documents = ref<KnowledgeDocument[]>([])
const total = ref(0)
const rebuilding = ref(false)
const error = ref<string | null>(null)

const tabs = [
  ['all', '全部'],
  ['case', '设计案例'],
  ['ref', '外部参考'],
  ['preset', 'Comfy 预设'],
] as const

const filtered = computed(() =>
  documents.value.filter((item) => tab.value === 'all' || item.type === tab.value),
)

const typeLabel: Record<string, string> = {
  case: '案例',
  ref: '参考',
  preset: '预设',
}

async function loadDocuments() {
  error.value = null
  const resp = await api.listKnowledgeDocuments()
  documents.value = resp.documents
  total.value = resp.total
}

async function rebuildIndex() {
  rebuilding.value = true
  error.value = null
  try {
    await api.reindexKnowledge()
    await loadDocuments()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '重建失败'
  } finally {
    rebuilding.value = false
  }
}

onMounted(async () => {
  try {
    await loadDocuments()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  }
})
</script>

<template>
  <div>
    <AppHeader active="knowledge" />
    <div class="ui-page">
      <div class="page-head">
        <div>
          <h2>设计知识库</h2>
          <p class="muted">Obsidian Vault · 向量索引 {{ total }} 条</p>
        </div>
        <button type="button" class="btn primary" @click="router.push({ name: 'knowledge-import' })">
          + 导入参考
        </button>
      </div>

      <div class="knowledge-tabs">
        <button
          v-for="[key, label] in tabs"
          :key="key"
          type="button"
          :class="{ active: tab === key }"
          @click="tab = key"
        >
          {{ label }}
        </button>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>

      <div class="knowledge-list">
        <article v-for="item in filtered" :key="item.id" class="know-item">
          <span class="type" :class="item.type">{{ typeLabel[item.type] ?? item.type }}</span>
          <div>
            <strong>{{ item.title }}</strong>
            <p class="tiny muted">{{ item.meta || item.path }}</p>
          </div>
        </article>
        <p v-if="!filtered.length && !error" class="muted">暂无文档，请导入参考或完成一次方案生成</p>
      </div>

      <button type="button" class="btn ghost" :disabled="rebuilding" @click="rebuildIndex">
        {{ rebuilding ? '重建中…' : '重建向量索引' }}
      </button>
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
  margin-bottom: 1rem;
}

.knowledge-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.knowledge-tabs button {
  border: 1px solid #444;
  background: var(--bg-panel);
  color: #ccc;
  border-radius: 999px;
  padding: 0.3rem 0.75rem;
  cursor: pointer;
}

.knowledge-tabs button.active {
  border-color: var(--accent);
  color: var(--accent);
}

.knowledge-list {
  display: grid;
  gap: 0.65rem;
  margin-bottom: 1rem;
}

.know-item {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 0.75rem;
  align-items: start;
  background: var(--bg-panel);
  border: 1px solid #333;
  border-radius: 8px;
  padding: 0.85rem;
}

.know-item .type {
  font-size: 0.72rem;
  padding: 0.2rem 0.45rem;
  border-radius: 999px;
  text-align: center;
  background: #333;
}

.know-item .type.case {
  background: #2c4a3e;
  color: #8fd4a8;
}

.know-item .type.ref {
  background: #3a3a4a;
  color: #aab;
}

.error-text {
  color: #d48f8f;
  margin-bottom: 0.75rem;
}

.tiny {
  font-size: 0.75rem;
}
</style>
