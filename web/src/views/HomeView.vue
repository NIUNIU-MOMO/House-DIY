<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'

import AppHeader from '@/components/AppHeader.vue'
import { useAppStore } from '@/stores/app'
import { useProjectsStore } from '@/stores/projects'

const router = useRouter()
const appStore = useAppStore()
const projectsStore = useProjectsStore()
const { omlxOnline, comfyuiOnline, vaultReady } = storeToRefs(appStore)
const { projects } = storeToRefs(projectsStore)

const searchQuery = ref('')
const statusFilter = ref('all')

const filteredProjects = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return projects.value.filter((p) => {
    if (statusFilter.value !== 'all' && p.status !== statusFilter.value) {
      return false
    }
    if (q && !p.name.toLowerCase().includes(q)) {
      return false
    }
    return true
  })
})

const statusLabel: Record<string, string> = {
  draft: '草稿',
  parsing: '解析中',
  review: '校对',
  designing: '设计中',
  delivered: '已完成',
}

async function handleNewProject() {
  const name = window.prompt('项目名称', '新建户型项目')
  if (!name?.trim()) {
    return
  }
  const project = await projectsStore.createProject(name.trim())
  router.push({ name: 'floorplan-upload', params: { id: project.id } })
}

function openProject(id: number) {
  router.push({ name: 'floorplan-upload', params: { id } })
}

onMounted(async () => {
  await Promise.all([appStore.fetchHealth(), projectsStore.fetchProjects()])
})
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="ui-page">
      <div class="page-head">
        <div>
          <h2>我的户型项目</h2>
          <p class="muted">全部数据保存在本机 · 已同步 Obsidian Vault</p>
        </div>
        <button type="button" class="btn primary" @click="handleNewProject">+ 新建项目</button>
      </div>

      <div class="service-grid" style="margin-bottom: 1.25rem">
        <div class="service-card">
          <h3>
            <span class="status-dot" :class="omlxOnline ? 'ok' : 'off'" />
            oMLX
          </h3>
          <p class="muted">{{ omlxOnline ? '运行中' : '离线' }}</p>
        </div>
        <div class="service-card">
          <h3>
            <span class="status-dot" :class="comfyuiOnline ? 'ok' : 'off'" />
            ComfyUI
          </h3>
          <p class="muted">{{ comfyuiOnline ? '运行中' : '离线' }}</p>
        </div>
        <div class="service-card">
          <h3>
            <span class="status-dot" :class="vaultReady ? 'ok' : 'off'" />
            Vault
          </h3>
          <p class="muted">{{ vaultReady ? '已就绪' : '未找到' }}</p>
        </div>
      </div>

      <div class="filter-row">
        <input v-model="searchQuery" type="search" placeholder="搜索项目名…" class="input" />
        <select v-model="statusFilter" class="input">
          <option value="all">全部状态</option>
          <option value="designing">设计中</option>
          <option value="delivered">已完成</option>
          <option value="parsing">解析中</option>
          <option value="draft">草稿</option>
        </select>
      </div>

      <div v-if="filteredProjects.length" class="project-grid">
        <article
          v-for="project in filteredProjects"
          :key="project.id"
          class="project-card"
          @click="openProject(project.id)"
        >
          <div
            class="thumb"
            :class="{ render: project.status === 'designing' || project.status === 'delivered' }"
          />
          <div class="card-body">
            <h3>{{ project.name }}</h3>
            <p class="muted">状态 · {{ statusLabel[project.status] ?? project.status }}</p>
            <div class="tags">
              <span :class="{ warn: project.status === 'parsing' || project.status === 'draft' }">
                {{ statusLabel[project.status] ?? project.status }}
              </span>
            </div>
          </div>
        </article>
      </div>
      <div v-else class="empty-state">
        <p>暂无项目，点击「新建项目」开始</p>
      </div>
    </div>
  </div>
</template>
