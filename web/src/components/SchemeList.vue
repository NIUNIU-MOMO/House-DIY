<script setup lang="ts">
import { computed } from 'vue'

import { api, type SchemeMeta } from '@/api/client'

const SCHEME_MAX = 10

const props = defineProps<{
  projectId: number
  schemes: SchemeMeta[]
  activeSchemeId: string | null
  loading?: boolean
}>()

const emit = defineEmits<{
  select: [schemeId: string]
  created: [scheme: SchemeMeta]
  deleted: [schemeId: string]
}>()

const canCreate = computed(() => props.schemes.length < SCHEME_MAX)

async function createScheme() {
  if (!canCreate.value) {
    window.alert(`每个项目最多 ${SCHEME_MAX} 套方案，请先手动删除旧方案。`)
    return
  }
  const name = `方案 ${String.fromCharCode(65 + props.schemes.length)}`
  try {
    const scheme = await api.createScheme(props.projectId, name)
    emit('created', scheme)
  } catch (e) {
    window.alert(e instanceof Error ? e.message : '创建失败')
  }
}

async function deleteScheme(scheme: SchemeMeta) {
  const proceed = window.confirm(`确定删除「${scheme.name}」？将移除该方案全部 2D/3D 产物。`)
  if (!proceed) {
    return
  }
  try {
    await api.deleteScheme(props.projectId, scheme.id)
    emit('deleted', scheme.id)
  } catch (e) {
    window.alert(e instanceof Error ? e.message : '删除失败')
  }
}
</script>

<template>
  <aside class="scheme-sidebar">
    <h4>方案列表</h4>
    <button
      v-for="scheme in schemes"
      :key="scheme.id"
      type="button"
      class="scheme-item"
      :class="{ active: scheme.id === activeSchemeId, stale: scheme.stale }"
      @click="emit('select', scheme.id)"
    >
      {{ scheme.name }}
      <span v-if="scheme.stale" class="stale-tag">待更新</span>
    </button>
    <button type="button" class="btn sm ghost block" :disabled="!canCreate || loading" @click="createScheme">
      + 新建方案
    </button>
    <button
      v-if="activeSchemeId && schemes.length > 1"
      type="button"
      class="btn sm ghost block danger"
      @click="deleteScheme(schemes.find((s) => s.id === activeSchemeId)!)"
    >
      删除当前方案
    </button>
  </aside>
</template>

<style scoped>
.scheme-sidebar {
  background: var(--bg-panel);
  border-right: 1px solid #333;
  padding: 1.25rem 1rem;
}

.scheme-sidebar h4 {
  font-size: 0.85rem;
  margin-bottom: 0.75rem;
}

.scheme-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 0.5rem 0.65rem;
  margin-bottom: 0.35rem;
  border: 1px solid #333;
  border-radius: 6px;
  background: #2a2824;
  color: #ddd;
  cursor: pointer;
  font-size: 0.85rem;
}

.scheme-item.active {
  border-color: #8fd4a8;
  background: #2c4a3e;
  color: #fff;
}

.scheme-item.stale {
  border-color: #8a5a24;
}

.stale-tag {
  display: inline-block;
  margin-left: 0.35rem;
  font-size: 0.65rem;
  color: #f0c14b;
}

.block {
  width: 100%;
  margin-top: 0.35rem;
}

.danger {
  color: #d48f8f;
  border-color: #5a3a3a;
}
</style>
