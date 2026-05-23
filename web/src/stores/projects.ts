import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api, type Project } from '@/api/client'

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref<Project[]>([])
  const loading = ref(false)

  async function fetchProjects() {
    loading.value = true
    try {
      projects.value = await api.listProjects()
    } finally {
      loading.value = false
    }
  }

  async function createProject(name: string) {
    const project = await api.createProject(name)
    projects.value.unshift(project)
    return project
  }

  async function deleteProject(id: number) {
    await api.deleteProject(id)
    projects.value = projects.value.filter((p) => p.id !== id)
  }

  return { projects, loading, fetchProjects, createProject, deleteProject }
})
