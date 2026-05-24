<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { storeToRefs } from 'pinia'

import AppHeader from '@/components/AppHeader.vue'
import ServiceLogModal from '@/components/ServiceLogModal.vue'
import { api, type OmlxModelConfig, type ServiceDetail } from '@/api/client'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const { health, loading, error } = storeToRefs(appStore)

const serviceDetails = ref<Record<string, ServiceDetail>>({})
const logService = ref<string | null>(null)
const restartingService = ref<string | null>(null)
const restartError = ref<string | null>(null)

const modelConfig = ref<OmlxModelConfig>({
  llm_model: '',
  vlm_model: '',
  vlm_model_cad: '',
  vlm_model_marketing: '',
  embed_model: '',
})
const availableModels = ref<string[]>([])
const omlxReachable = ref(false)
const modelsLoading = ref(false)
const modelsSaving = ref(false)
const modelsError = ref<string | null>(null)
const modelsSaved = ref(false)

const modelFields: Array<{ key: keyof OmlxModelConfig; label: string; hint: string; required?: boolean }> = [
  { key: 'llm_model', label: 'LLM', hint: '文本生成，如 house-llm', required: true },
  { key: 'vlm_model', label: 'VLM（默认）', hint: '户型解析默认模型，如 house-vlm-pro', required: true },
  { key: 'vlm_model_cad', label: 'VLM（CAD 线稿）', hint: '留空则使用默认 VLM', required: false },
  { key: 'vlm_model_marketing', label: 'VLM（营销彩图）', hint: '留空则使用默认 VLM', required: false },
  { key: 'embed_model', label: 'Embedding', hint: '知识库向量，如 house-embed', required: true },
]

const serviceEntries = computed(() => {
  if (!health.value) {
    return []
  }
  return Object.entries(health.value.services).map(([key, value]) => ({
    key,
    value,
    detail: serviceDetails.value[key] ?? {
      label: key,
      web_url: '#',
      external: true,
    },
  }))
})

function modelOptions(fieldKey: keyof OmlxModelConfig) {
  const current = modelConfig.value[fieldKey]
  const merged = new Set(availableModels.value)
  if (current) {
    merged.add(current)
  }
  return Array.from(merged).sort()
}

function serviceLabel(name: string, value?: string) {
  if (name === 'vault') {
    return value === 'ready' ? '已就绪' : '未找到'
  }
  return value === 'online' ? '运行中' : '离线'
}

function showRestart(name: string, value?: string, detail?: ServiceDetail) {
  if (name === 'omlx') {
    return false
  }
  const restartable = detail?.restartable ?? name !== 'omlx'
  return restartable && !isOk(name, value)
}

function isOk(name: string, value?: string) {
  if (name === 'vault') {
    return value === 'ready'
  }
  return value === 'online'
}

async function loadHealth() {
  await appStore.fetchHealth()
  serviceDetails.value = appStore.health?.service_details ?? {}
}

async function loadModelConfig() {
  modelsLoading.value = true
  modelsError.value = null
  modelsSaved.value = false
  try {
    const response = await api.getOmlxModels()
    modelConfig.value = {
      llm_model: response.llm_model,
      vlm_model: response.vlm_model,
      vlm_model_cad: response.vlm_model_cad,
      vlm_model_marketing: response.vlm_model_marketing,
      embed_model: response.embed_model,
    }
    availableModels.value = response.available_models
    omlxReachable.value = response.omlx_reachable
  } catch (err) {
    modelsError.value = err instanceof Error ? err.message : '加载模型配置失败'
  } finally {
    modelsLoading.value = false
  }
}

async function saveModelConfig() {
  modelsSaving.value = true
  modelsError.value = null
  modelsSaved.value = false
  try {
    const saved = await api.updateOmlxModels(modelConfig.value)
    modelConfig.value = saved
    modelsSaved.value = true
  } catch (err) {
    modelsError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    modelsSaving.value = false
  }
}

async function refreshAll() {
  restartError.value = null
  await Promise.all([loadHealth(), loadModelConfig()])
}

async function restartComponent(serviceKey: string) {
  restartingService.value = serviceKey
  restartError.value = null
  try {
    await api.restartService(serviceKey)
    await loadHealth()
  } catch (err) {
    restartError.value = err instanceof Error ? err.message : '重启失败'
  } finally {
    restartingService.value = null
  }
}

function openLogs(serviceKey: string) {
  logService.value = serviceKey
}

function closeLogs() {
  logService.value = null
}

const activeLogLabel = computed(() => {
  if (!logService.value) {
    return ''
  }
  return serviceDetails.value[logService.value]?.label ?? logService.value
})

onMounted(refreshAll)
</script>

<template>
  <div>
    <AppHeader active="settings" />
    <div class="ui-page settings-page">
      <div class="page-toolbar">
        <button
          type="button"
          class="icon-refresh-btn"
          :disabled="loading || modelsLoading"
          title="刷新状态"
          aria-label="刷新状态"
          @click="refreshAll()"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path
              fill="currentColor"
              d="M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08a5.99 5.99 0 0 1-5.65 4c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"
            />
          </svg>
        </button>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>
      <p v-if="restartError" class="error-text">{{ restartError }}</p>

      <div v-if="health" class="service-grid">
        <div v-for="item in serviceEntries" :key="item.key" class="service-card">
          <div class="service-card-head">
            <h3>
              <span class="status-dot" :class="isOk(item.key, item.value) ? 'ok' : 'off'" />
              <a
                v-if="item.detail.web_url && item.detail.external"
                :href="item.detail.web_url"
                class="service-link"
                target="_blank"
                rel="noopener noreferrer"
              >
                {{ item.detail.label }}
              </a>
              <RouterLink
                v-else-if="item.detail.web_url"
                :to="item.detail.web_url"
                class="service-link"
              >
                {{ item.detail.label }}
              </RouterLink>
              <span v-else class="service-name">{{ item.detail.label }}</span>
            </h3>
            <div class="service-card-actions">
              <button
                v-if="showRestart(item.key, item.value, item.detail)"
                type="button"
                class="icon-action-btn"
                :disabled="restartingService === item.key"
                title="重启组件"
                :aria-label="`重启 ${item.detail.label}`"
                @click="restartComponent(item.key)"
              >
                <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                  <path
                    fill="currentColor"
                    d="M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08a5.99 5.99 0 0 1-5.65 4c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"
                  />
                </svg>
              </button>
              <button type="button" class="btn sm ghost" @click="openLogs(item.key)">日志</button>
            </div>
          </div>
          <p class="muted">{{ serviceLabel(item.key, item.value) }}</p>
        </div>
      </div>

      <div v-else-if="loading" class="empty-state">
        <p>正在检测服务状态…</p>
      </div>

      <section class="model-config-panel">
        <div class="model-config-head">
          <div>
            <h2>oMLX 模型 Alias</h2>
            <p class="muted">
              切换户型解析等任务使用的模型 alias；保存后立即生效，无需重启 API。
            </p>
          </div>
          <button
            type="button"
            class="btn primary"
            :disabled="modelsLoading || modelsSaving"
            @click="saveModelConfig"
          >
            {{ modelsSaving ? '保存中…' : '保存配置' }}
          </button>
        </div>

        <p v-if="modelsError" class="error-text">{{ modelsError }}</p>
        <p v-else-if="modelsSaved" class="success-text">配置已保存并生效</p>
        <p v-if="!omlxReachable && !modelsLoading" class="warn-text">
          无法连接 oMLX，下拉列表可能不完整，可直接输入 alias。
        </p>

        <div v-if="modelsLoading" class="empty-state">
          <p>正在加载模型配置…</p>
        </div>

        <form v-else class="model-config-form" @submit.prevent="saveModelConfig">
          <div v-for="field in modelFields" :key="field.key" class="form-row">
            <label :for="`model-${field.key}`">
              {{ field.label }}
              <span v-if="!field.required" class="optional-tag">可选</span>
            </label>
            <input
              :id="`model-${field.key}`"
              v-model="modelConfig[field.key]"
              class="input"
              :list="`model-options-${field.key}`"
              :placeholder="field.hint"
              :required="field.required"
            />
            <datalist :id="`model-options-${field.key}`">
              <option v-for="option in modelOptions(field.key)" :key="option" :value="option" />
            </datalist>
            <p class="field-hint muted">{{ field.hint }}</p>
          </div>
        </form>
      </section>
    </div>

    <ServiceLogModal
      v-if="logService"
      :service="logService"
      :service-label="activeLogLabel"
      :open="Boolean(logService)"
      @close="closeLogs"
    />
  </div>
</template>

<style scoped>
.settings-page {
  padding-top: 0.75rem;
}

.page-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 1rem;
}

.icon-refresh-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: 1px solid #444;
  background: var(--bg-panel);
  color: #ddd;
  display: grid;
  place-items: center;
  cursor: pointer;
}

.icon-refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.icon-refresh-btn:not(:disabled):hover {
  border-color: var(--accent);
  color: var(--accent);
}

.service-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.35rem;
}

.service-card-head h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
}

.service-link {
  color: inherit;
  text-decoration: none;
}

.service-link:hover {
  color: var(--accent);
  text-decoration: underline;
}

.service-name {
  color: inherit;
}

.service-card-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.icon-action-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid #444;
  background: var(--bg-panel);
  color: #ddd;
  display: grid;
  place-items: center;
  cursor: pointer;
}

.icon-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.icon-action-btn:not(:disabled):hover {
  border-color: var(--accent);
  color: var(--accent);
}

.error-text {
  color: #d48f8f;
  margin-bottom: 1rem;
}

.success-text {
  color: #8fbf9f;
  margin-bottom: 1rem;
}

.warn-text {
  color: #d4b48f;
  margin-bottom: 1rem;
}

.model-config-panel {
  margin-top: 2rem;
  padding: 1.25rem;
  border: 1px solid #333;
  border-radius: 12px;
  background: var(--bg-panel);
}

.model-config-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.model-config-head h2 {
  margin: 0 0 0.35rem;
  font-size: 1.1rem;
}

.model-config-form {
  display: grid;
  gap: 1rem;
  max-width: 560px;
}

.form-row label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}

.optional-tag {
  font-size: 0.75rem;
  color: #888;
  border: 1px solid #444;
  border-radius: 4px;
  padding: 0 0.35rem;
}

.field-hint {
  margin: 0.35rem 0 0;
  font-size: 0.85rem;
}
</style>
