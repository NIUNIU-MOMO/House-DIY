<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import { api } from '@/api/client'

const router = useRouter()
const title = ref('')
const tags = ref('')
const file = ref<File | null>(null)
const submitting = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  file.value = target.files?.[0] ?? null
  if (file.value && !title.value) {
    title.value = file.value.name.replace(/\.[^.]+$/, '')
  }
}

async function submitImport() {
  if (!file.value) {
    error.value = '请选择文件'
    return
  }
  submitting.value = true
  error.value = null
  success.value = null
  try {
    const result = await api.importKnowledge(file.value, {
      title: title.value || undefined,
      tags: tags.value || undefined,
    })
    success.value = `已导入：${result.title}（${result.path}）`
    setTimeout(() => router.push({ name: 'knowledge-list' }), 800)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '导入失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div>
    <AppHeader active="knowledge" />
    <div class="ui-page narrow">
      <h2>导入外部参考</h2>
      <p class="muted">将写入 Obsidian References/ 并由 oMLX VLM 生成摘要</p>

      <label class="upload-zone">
        <input type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" hidden @change="onFileChange" />
        <p>{{ file ? file.name : 'PDF / PNG / JPG · 点击选择' }}</p>
      </label>

      <div class="form-row">
        <label>标题</label>
        <input v-model="title" class="input" placeholder="例如：北欧客厅参考" />
      </div>

      <div class="form-row">
        <label>标签（逗号分隔）</label>
        <input v-model="tags" class="input" placeholder="北欧, 客厅, 参考" />
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>
      <p v-if="success" class="success-text">{{ success }}</p>

      <div class="footer-actions">
        <button type="button" class="btn primary" :disabled="submitting" @click="submitImport">
          {{ submitting ? '导入中…' : '导入并建立索引' }}
        </button>
        <button type="button" class="btn ghost" @click="router.push({ name: 'knowledge-list' })">取消</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
h2 {
  font-family: var(--serif);
}

.narrow {
  max-width: 560px;
}

.upload-zone {
  display: block;
  border: 2px dashed #444;
  border-radius: var(--radius);
  padding: 2rem;
  text-align: center;
  margin: 1rem 0;
  cursor: pointer;
}

.form-row {
  margin-bottom: 0.85rem;
}

.form-row label {
  display: block;
  font-size: 0.85rem;
  color: #aaa;
  margin-bottom: 0.35rem;
}

.form-row .input {
  width: 100%;
}

.footer-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.error-text {
  color: #d48f8f;
}

.success-text {
  color: #8fd4a8;
}
</style>
