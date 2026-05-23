<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'

import AppHeader from '@/components/AppHeader.vue'
import { useProjectsStore } from '@/stores/projects'
import { resolveProjectEntry } from '@/utils/projectNavigation'

const router = useRouter()
const projectsStore = useProjectsStore()
const { projects } = storeToRefs(projectsStore)

const searchQuery = ref('')
const statusFilter = ref('all')

const DEFAULT_DRAFT_NAME = '新建户型项目'

const visibleProjects = computed(() =>
  projects.value.filter(
    (project) => !(project.status === 'draft' && project.name === DEFAULT_DRAFT_NAME),
  ),
)

const filteredProjects = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return visibleProjects.value.filter((p) => {
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
  const name = window.prompt('项目名称', DEFAULT_DRAFT_NAME)
  if (!name?.trim()) {
    return
  }
  const project = await projectsStore.createProject(name.trim())
  router.push({ name: 'floorplan-upload', params: { id: project.id } })
}

async function openProject(id: number) {
  const project = projects.value.find((item) => item.id === id)
  const target = await resolveProjectEntry(id, project)
  router.push(target)
}

onMounted(() => {
  projectsStore.fetchProjects()
})
</script>

<template>
  <div>
    <AppHeader active="projects" />
    <div class="ui-page">
      <div class="page-head">
        <h2>我的户型项目</h2>
        <button type="button" class="btn primary" @click="handleNewProject">+ 新建项目</button>
      </div>

      <div class="filter-row">
        <input v-model="searchQuery" type="search" placeholder="搜索项目名…" class="input" />
        <select v-model="statusFilter" class="input">
          <option value="all">全部状态</option>
          <option value="delivered">已完成</option>
          <option value="designing">设计中</option>
          <option value="review">校对</option>
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
          <div class="thumb" :class="{ 'has-cover': Boolean(project.cover_image_url) }">
            <img
              v-if="project.cover_image_url"
              :src="project.cover_image_url"
              :alt="`${project.name} 封面`"
              loading="lazy"
            />
          </div>
          <div class="card-body">
            <h3>{{ project.name }}</h3>
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
