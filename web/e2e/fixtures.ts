import type { Page } from '@playwright/test'

const PROJECT_ID = 1

export const mockProject = {
  id: PROJECT_ID,
  name: 'E2E 样本',
  status: 'delivered',
  max_step: 'preview',
  active_scheme_id: 'scheme-a',
  annotation_confirmed_at: '2026-01-01T00:00:00Z',
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
  cover_image_url: `/api/v1/projects/${PROJECT_ID}/renders/r1/image`,
}

export const mockStorageSettings = {
  output_root: '',
  effective_output_root: '/tmp/house-diy-output',
  writable: true,
  writable_error: null,
}

export const mockSchemes = [
  {
    id: 'scheme-a',
    name: '方案 A',
    status: 'ready',
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-01T00:00:00',
  },
]

export const mockFloorplan = {
  status: 'confirmed',
  scale: 100,
  walls: [{ id: 'w1', points: [{ x: 0, y: 0 }, { x: 100, y: 0 }] }],
  rooms: [
    {
      id: 'r1',
      name: '客厅',
      polygon: [
        { x: 0, y: 0 },
        { x: 100, y: 0 },
        { x: 100, y: 100 },
        { x: 0, y: 100 },
      ],
      area: 25,
    },
    {
      id: 'r2',
      name: '主卧',
      polygon: [
        { x: 100, y: 0 },
        { x: 200, y: 0 },
        { x: 200, y: 100 },
        { x: 100, y: 100 },
      ],
      area: 20,
    },
  ],
  openings: [],
  source_url: null,
  validation: { level: 'pass', issues: [] },
}

export const mockFloorplanDraftError = {
  status: 'draft',
  scale: null,
  walls: [{ id: 'w1', points: [{ x: 0, y: 0 }, { x: 100, y: 0 }] }],
  rooms: [
    {
      id: 'r1',
      name: '客厅',
      polygon: [
        { x: 0, y: 0 },
        { x: 100, y: 0 },
        { x: 100, y: 100 },
        { x: 0, y: 100 },
      ],
      area: 25,
    },
    {
      id: 'r2',
      name: '主卧',
      polygon: [
        { x: 0, y: 0 },
        { x: 100, y: 0 },
        { x: 100, y: 100 },
        { x: 0, y: 100 },
      ],
      area: 20,
    },
  ],
  openings: [],
  source_url: null,
  validation: {
    level: 'error',
    issues: [
      {
        code: 'ROOM_DUPLICATE_POLYGON',
        severity: 'error',
        message: '主卧(r2) 与 客厅(r1) polygon 完全相同',
        room_ids: ['r1', 'r2'],
      },
    ],
  },
}

export const mockDesignSpec = {
  version: 1,
  globalStyle: '现代简约',
  rooms: [
    { id: 'r1', name: '客厅' },
    { id: 'r2', name: '主卧' },
  ],
}

export const mockRenders = {
  rooms: [
    {
      room_id: 'r1',
      room_name: '客厅',
      filename: 'living.png',
      prompt: 'modern living room',
      negative: '',
      workflow: 'flux_interior_t2i',
      created_at: '2026-01-01T00:00:00',
      image_url: '/api/v1/projects/1/renders/r1/image',
    },
  ],
}

export const mockScene = {
  version: 1,
  gltf: 'scene.gltf',
  status: 'ready',
  gltf_url: `/api/v1/projects/${PROJECT_ID}/scene/gltf`,
  rooms: [{ id: 'r1', name: '客厅', bounds: { min: { x: 0, y: 0, z: 0 }, max: { x: 5, y: 3, z: 5 } }, collision_boxes: [], furniture: [] }],
  portals: [],
  active_room: 'r1',
}

export const mockHealth = {
  status: 'ok',
  services: { omlx: 'online', comfyui: 'offline', redis: 'online', vault: 'ready' },
  service_details: {
    omlx: { label: 'oMLX', web_url: 'http://127.0.0.1:8000/admin', external: true, restartable: false },
    comfyui: { label: 'ComfyUI', web_url: 'http://127.0.0.1:8188', external: true, restartable: true },
    redis: { label: 'Redis', web_url: '', external: false, restartable: true },
    vault: { label: 'Vault', web_url: '/knowledge', external: false, restartable: true },
  },
}

export const mockOmlxModels = {
  llm_model: 'house-llm',
  vlm_model: 'house-vlm-pro',
  vlm_model_cad: '',
  vlm_model_marketing: '',
  embed_model: 'house-embed',
  available_models: ['house-llm', 'house-vlm', 'house-vlm-pro', 'house-embed'],
  omlx_reachable: true,
}

export const mockKnowledgeDocuments = {
  total: 2,
  documents: [
    { id: 'case-1', title: '北欧客厅案例', type: 'case', meta: '2026', path: 'Cases/sample.md', source: 'vault' },
    { id: 'ref-1', title: '杂志参考', type: 'ref', meta: '', path: 'References/mag.jpg', source: 'vault' },
  ],
}

export const mockKnowledgeSearch = {
  query: '现代简约',
  results: [
    { id: 'case-1', title: '北欧客厅案例', score: 0.92, desc: '暖白墙面', type: 'case' },
  ],
}

export const mockTaskRunning = {
  id: 10,
  project_id: PROJECT_ID,
  type: 'design_generate',
  status: 'running',
  progress: 50,
  step: 2,
  step_label: 'ComfyUI 2D 渲染',
  error: null,
}

export const mockTaskDone = {
  ...mockTaskRunning,
  status: 'done',
  progress: 100,
  step: 4,
  step_label: '完成',
}

/**
 * 注册常用 API mock，覆盖原型 01–13 主路由所需接口
 */
export async function installCoreMocks(page: Page, options?: { projects?: unknown[] }) {
  const projects = options?.projects ?? [mockProject]

  await page.route('**/api/v1/health', (route) =>
    route.fulfill({ json: mockHealth }),
  )
  await page.route('**/api/v1/health/omlx-models', (route) => {
    if (route.request().method() === 'PUT') {
      return route.fulfill({ json: mockOmlxModels })
    }
    return route.fulfill({ json: mockOmlxModels })
  })
  await page.route('**/api/v1/settings/storage', (route) => {
    if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON() as { output_root?: string }
      return route.fulfill({
        json: {
          ...mockStorageSettings,
          output_root: body.output_root ?? mockStorageSettings.output_root,
          effective_output_root: body.output_root || mockStorageSettings.effective_output_root,
        },
      })
    }
    return route.fulfill({ json: mockStorageSettings })
  })
  await page.route('**/api/v1/health/restart/**', (route) =>
    route.fulfill({
      json: {
        service: 'comfyui',
        success: true,
        exit_code: 0,
        output: '[ComfyUI] 重启完成',
      },
    }),
  )
  await page.route('**/api/v1/health/logs/**', (route) =>
    route.fulfill({
      json: {
        service: 'omlx',
        lines: ['[mock] service running'],
        offset: 100,
        exists: true,
        path: '/tmp/mock.log',
        message: null,
      },
    }),
  )
  await page.route('**/api/v1/projects', (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({ json: projects })
    }
    return route.continue()
  })
  await page.route(`**/api/v1/projects/${PROJECT_ID}`, (route) =>
    route.fulfill({ json: mockProject }),
  )
  await page.route(`**/api/v1/projects/${PROJECT_ID}/floorplan`, (route) =>
    route.fulfill({ json: mockFloorplan }),
  )
  await page.route(`**/api/v1/projects/${PROJECT_ID}/schemes`, (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({ json: mockSchemes })
    }
    return route.continue()
  })
  await page.route(`**/api/v1/projects/${PROJECT_ID}/schemes/*/spec`, (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({ json: mockDesignSpec })
    }
    return route.continue()
  })
  await page.route(`**/api/v1/projects/${PROJECT_ID}/design/spec`, (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({ json: mockDesignSpec })
    }
    return route.continue()
  })
  await page.route(`**/api/v1/projects/${PROJECT_ID}/renders`, (route) =>
    route.fulfill({ json: mockRenders }),
  )
  await page.route(`**/api/v1/projects/${PROJECT_ID}/scene`, (route) =>
    route.fulfill({ json: mockScene }),
  )
  await page.route('**/api/v1/knowledge/documents', (route) =>
    route.fulfill({ json: mockKnowledgeDocuments }),
  )
  await page.route('**/api/v1/knowledge/search**', (route) =>
    route.fulfill({ json: mockKnowledgeSearch }),
  )
}

export async function installEditorMocks(page: Page) {
  await installCoreMocks(page, {
    projects: [{ ...mockProject, status: 'review', max_step: 'annotate', name: 'E2E 标注样本' }],
  })
  await page.route(`**/api/v1/projects/${PROJECT_ID}/floorplan/annotation`, (route) => {
    if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON() as Record<string, unknown>
      return route.fulfill({
        json: {
          ...mockFloorplanDraftError,
          ...body,
          validation: { level: 'pass', issues: [] },
        },
      })
    }
    return route.continue()
  })
  await page.route(`**/api/v1/projects/${PROJECT_ID}/floorplan/confirm`, (route) =>
    route.fulfill({
      status: 422,
      json: {
        detail: {
          message: '户型质检未通过，请修正后再确认',
          validation: mockFloorplanDraftError.validation,
        },
      },
    }),
  )
  await page.route(`**/api/v1/projects/${PROJECT_ID}/floorplan`, (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({ json: mockFloorplanDraftError })
    }
    return route.continue()
  })
}

export async function installParseMocks(page: Page) {
  await installCoreMocks(page, {
    projects: [{ ...mockProject, status: 'parsing', max_step: 'parse' }],
  })
  await page.route(`**/api/v1/projects/${PROJECT_ID}/tasks/*`, (route) =>
    route.fulfill({ json: mockTaskDone }),
  )
}

export async function installGenerateMocks(page: Page) {
  await installCoreMocks(page, {
    projects: [{ ...mockProject, status: 'designing', max_step: 'design' }],
  })
  await page.route(`**/api/v1/projects/${PROJECT_ID}/tasks/*`, (route) =>
    route.fulfill({ json: mockTaskRunning }),
  )
}

export { PROJECT_ID }
