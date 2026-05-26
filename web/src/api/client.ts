export interface HealthResponse {
  status: string
  services: {
    omlx: string
    comfyui: string
    redis: string
    vault: string
  }
  service_details?: Record<string, ServiceDetail>
}

export interface ServiceDetail {
  label: string
  web_url: string
  external: boolean
  restartable?: boolean
}

export interface ServiceRestartResult {
  service: string
  success: boolean
  exit_code: number
  output: string
}

export interface ServiceLogChunk {
  service: string
  lines: string[]
  offset: number
  exists: boolean
  path: string | null
  message: string | null
}

export interface OmlxModelConfig {
  llm_model: string
  vlm_model: string
  vlm_model_cad: string
  vlm_model_marketing: string
  embed_model: string
}

export interface OmlxModelConfigResponse extends OmlxModelConfig {
  available_models: string[]
  omlx_reachable: boolean
}

export interface Project {
  id: number
  name: string
  status: string
  created_at: string
  updated_at: string
  cover_image_url?: string | null
}

export type PlanType = 'cad_lineart' | 'marketing_color' | 'unknown'

export interface FloorPlan {
  status: string
  scale: number | null
  walls: Array<{ id: string; points: Array<{ x: number; y: number }> }>
  rooms: Array<{ id: string; name: string; polygon: Array<{ x: number; y: number }>; area?: number | null }>
  openings: unknown[]
  source_image?: string | null
  source_url?: string | null
  original_filename?: string | null
  estimated_area?: number | null
  plan_type?: PlanType | null
  has_watermark?: boolean | null
  plan_type_label?: string | null
  plan_type_message?: string | null
}

export interface Task {
  id: number
  project_id: number
  type: string
  status: 'pending' | 'running' | 'done' | 'failed' | 'cancelled'
  progress: number
  step: number
  step_label: string
  error: string | null
  logs?: string[]
}

export interface RenderRecord {
  room_id: string
  room_name: string
  filename: string
  prompt: string
  negative: string
  workflow: string
  created_at: string
  image_url: string
}

export interface SceneRoomMeta {
  id: string
  name: string
  bounds: {
    min: { x: number; y: number; z: number }
    max: { x: number; y: number; z: number }
  }
  collision_boxes: Array<{
    min: [number, number, number]
    max: [number, number, number]
  }>
  portals?: ScenePortal[]
  furniture: Array<{
    sku: string
    name: string
    position: [number, number, number]
    rotation: number
    size: [number, number, number]
  }>
}

export interface ScenePortal {
  id: string
  source_room_id: string
  target_room_id: string
  target_room_name: string
  trigger: { min: [number, number, number]; max: [number, number, number] }
  spawn: [number, number, number]
}

export interface ScenePackage {
  version: number
  gltf: string
  status: string
  gltf_url: string
  rooms: SceneRoomMeta[]
  portals: ScenePortal[]
  active_room: string | null
}

export interface RefineDiffItem {
  tag: string
  text: string
  room_id?: string | null
}

export interface RefinePreview {
  instruction: string
  diff: RefineDiffItem[]
  patch: Record<string, unknown>
  affected_room_ids: string[]
}

export interface KnowledgeDocument {
  id: string
  title: string
  type: string
  meta: string
  path: string
  source: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { ...(init?.headers as Record<string, string>) }
  const isFormData = init?.body instanceof FormData
  if (!isFormData && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const resp = await fetch(`/api/v1${path}`, {
    ...init,
    headers,
  })
  if (!resp.ok) {
    throw new Error(`API ${resp.status}: ${path}`)
  }
  if (resp.status === 204) {
    return undefined as T
  }
  return resp.json() as Promise<T>
}

export const api = {
  health: () => request<HealthResponse>('/health'),
  fetchServiceLogs: (service: string, offset = 0, tail = 200) =>
    request<ServiceLogChunk>(
      `/health/logs/${service}?offset=${offset}&tail=${tail}`,
    ),
  getOmlxModels: () => request<OmlxModelConfigResponse>('/health/omlx-models'),
  updateOmlxModels: (payload: OmlxModelConfig) =>
    request<OmlxModelConfig>('/health/omlx-models', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  restartService: (service: string) =>
    request<ServiceRestartResult>(`/health/restart/${service}`, { method: 'POST' }),
  listProjects: () => request<Project[]>('/projects'),
  createProject: (name: string) =>
    request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),
  deleteProject: (id: number) =>
    request<void>(`/projects/${id}`, { method: 'DELETE' }),
  getProject: (id: number) => request<Project>(`/projects/${id}`),
  getFloorplan: (projectId: number) => request<FloorPlan>(`/projects/${projectId}/floorplan`),
  uploadFloorplan: (
    projectId: number,
    file: File,
    options?: { name?: string; estimatedArea?: number },
  ) => {
    const form = new FormData()
    form.append('file', file)
    if (options?.name) {
      form.append('name', options.name)
    }
    if (options?.estimatedArea != null) {
      form.append('estimated_area', String(options.estimatedArea))
    }
    return request<FloorPlan>(`/projects/${projectId}/floorplan`, {
      method: 'POST',
      body: form,
    })
  },
  startFloorplanParse: (projectId: number) =>
    request<Task>(`/projects/${projectId}/floorplan/parse`, { method: 'POST' }),
  getTask: (projectId: number, taskId: number) =>
    request<Task>(`/projects/${projectId}/tasks/${taskId}`),
  cancelTask: (projectId: number, taskId: number) =>
    request<Task>(`/projects/${projectId}/tasks/${taskId}/cancel`, { method: 'POST' }),
  updateFloorplan: (projectId: number, payload: Record<string, unknown>) =>
    request<FloorPlan>(`/projects/${projectId}/floorplan`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  setFloorplanScale: (
    projectId: number,
    pointA: { x: number; y: number },
    pointB: { x: number; y: number },
    distanceM: number,
  ) =>
    request<FloorPlan>(`/projects/${projectId}/floorplan/scale`, {
      method: 'POST',
      body: JSON.stringify({ point_a: pointA, point_b: pointB, distance_m: distanceM }),
    }),
  searchKnowledge: (q: string, topK = 3) =>
    request<{ query: string; results: Array<{ id: string; title: string; score: number; desc?: string; type?: string }> }>(
      `/knowledge/search?q=${encodeURIComponent(q)}&top_k=${topK}`,
    ),
  listKnowledgeDocuments: () =>
    request<{ total: number; documents: KnowledgeDocument[] }>('/knowledge/documents'),
  reindexKnowledge: () =>
    request<{ indexed: number; removed: number }>('/knowledge/reindex', { method: 'POST' }),
  importKnowledge: (file: File, options?: { title?: string; tags?: string }) => {
    const form = new FormData()
    form.append('file', file)
    if (options?.title) {
      form.append('title', options.title)
    }
    if (options?.tags) {
      form.append('tags', options.tags)
    }
    return request<{ path: string; title: string; indexed: boolean }>('/knowledge/import', {
      method: 'POST',
      body: form,
    })
  },
  getDesignSpec: (projectId: number) =>
    request<Record<string, unknown>>(`/projects/${projectId}/design/spec`),
  generateDesign: (
    projectId: number,
    payload: { brief: string; globalStyle?: string; useRag?: boolean },
  ) =>
    request<Task>(`/projects/${projectId}/design/generate`, {
      method: 'POST',
      body: JSON.stringify({
        brief: payload.brief,
        global_style: payload.globalStyle,
        use_rag: payload.useRag ?? true,
      }),
    }),
  listRenders: (projectId: number) =>
    request<{ rooms: RenderRecord[] }>(`/projects/${projectId}/renders`),
  regenerateRender: (projectId: number, roomId: string) =>
    request<Task>(`/projects/${projectId}/renders/${roomId}/regenerate`, { method: 'POST' }),
  getScene: (projectId: number) => request<ScenePackage>(`/projects/${projectId}/scene`),
  previewRefine: (projectId: number, instruction: string) =>
    request<RefinePreview>(`/projects/${projectId}/design/refine`, {
      method: 'POST',
      body: JSON.stringify({ instruction }),
    }),
  applyRefine: (
    projectId: number,
    payload: { patch: Record<string, unknown>; affectedRoomIds: string[]; updateObsidian?: boolean },
  ) =>
    request<Task>(`/projects/${projectId}/design/refine/apply`, {
      method: 'POST',
      body: JSON.stringify({
        patch: payload.patch,
        affected_room_ids: payload.affectedRoomIds,
        update_obsidian: payload.updateObsidian ?? false,
      }),
    }),
}
