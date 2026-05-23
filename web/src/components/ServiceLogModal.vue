<script setup lang="ts">
import { nextTick, onUnmounted, ref, watch } from 'vue'

import { api } from '@/api/client'

const props = defineProps<{
  service: string
  serviceLabel: string
  open: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const lines = ref<string[]>([])
const logOffset = ref(0)
const logPath = ref<string | null>(null)
const logMessage = ref<string | null>(null)
const loading = ref(false)
const logBox = ref<HTMLElement | null>(null)

const POLL_MS = 2000
let pollTimer: ReturnType<typeof setInterval> | null = null

async function fetchLogs(initial = false) {
  if (!props.open) {
    return
  }
  loading.value = initial
  try {
    const chunk = await api.fetchServiceLogs(props.service, initial ? 0 : logOffset.value)
    logPath.value = chunk.path
    logMessage.value = chunk.message

    if (initial) {
      lines.value = chunk.lines
    } else if (chunk.lines.length) {
      lines.value = [...lines.value, ...chunk.lines].slice(-2000)
    }

    logOffset.value = chunk.offset
    await nextTick()
    if (logBox.value) {
      logBox.value.scrollTop = logBox.value.scrollHeight
    }
  } catch (e) {
    logMessage.value = e instanceof Error ? e.message : '读取日志失败'
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  void fetchLogs(true)
  pollTimer = setInterval(() => {
    void fetchLogs(false)
  }, POLL_MS)
}

function stopPolling() {
  if (null != pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(
  () => [props.open, props.service] as const,
  ([isOpen]) => {
    if (isOpen) {
      lines.value = []
      logOffset.value = 0
      startPolling()
      return
    }
    stopPolling()
  },
  { immediate: true },
)

onUnmounted(stopPolling)
</script>

<template>
  <div v-if="open" class="log-modal-backdrop" @click.self="emit('close')">
    <div class="log-modal" role="dialog" aria-modal="true" :aria-label="`${serviceLabel} 运行日志`">
      <header class="log-modal-head">
        <div>
          <h3>{{ serviceLabel }} 运行日志</h3>
          <p v-if="logPath" class="tiny muted">{{ logPath }}</p>
          <p v-else-if="logMessage" class="tiny warn">{{ logMessage }}</p>
        </div>
        <button type="button" class="icon-btn-close" aria-label="关闭" @click="emit('close')">×</button>
      </header>
      <pre ref="logBox" class="log-box">{{ lines.join('\n') || (loading ? '加载中…' : '暂无日志') }}</pre>
      <footer class="log-modal-foot">
        <span class="tiny muted">每 {{ POLL_MS / 1000 }} 秒自动刷新</span>
        <button type="button" class="btn sm ghost" :disabled="loading" @click="fetchLogs(true)">立即刷新</button>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.log-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.log-modal {
  width: min(920px, 100%);
  max-height: min(80vh, 720px);
  background: #1e1c18;
  border: 1px solid #444;
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
}

.log-modal-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem 1rem 0.75rem;
  border-bottom: 1px solid #333;
}

.log-modal-head h3 {
  font-size: 1rem;
  margin-bottom: 0.25rem;
}

.icon-btn-close {
  border: none;
  background: transparent;
  color: #aaa;
  font-size: 1.5rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 0.25rem;
}

.log-box {
  flex: 1;
  margin: 0;
  padding: 1rem;
  overflow: auto;
  font-size: 0.78rem;
  line-height: 1.45;
  color: #c8c4bc;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.log-modal-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.65rem 1rem;
  border-top: 1px solid #333;
}

.tiny {
  font-size: 0.75rem;
}

.warn {
  color: #d9b44a;
}
</style>
