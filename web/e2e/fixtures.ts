import type { Page } from '@playwright/test'

const PROJECT_ID = 1

export const mockProject = {
  id: PROJECT_ID,
  name: 'E2E 样本',
  status: 'delivered',
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
}

export const mockFloorplan = {
  status: 'confirmed',
  scale: 100,
  walls: [{ id: 'w1', points: [{ x: 0, y: 0 }, { x: 100, y: 0 }] }],
  rooms: [
    { id: 'r1', name: '客厅', polygon: [{ x: 0, y: 0 }, { x: 50, y: 50 }], area: 25 },
    { id: 'r2', name: '主卧', polygon: [{ x: 50, y: 0 }, { x: 100, y: 50 }], area: 20 },
  ],
  openings: [],
  source_url: null,
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
  services: { omlx: 'online', comfyui: 'online', vault: 'ready' },
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

export async function installParseMocks(page: Page) {
  await installCoreMocks(page, {
    projects: [{ ...mockProject, status: 'parsing' }],
  })
  await page.route(`**/api/v1/projects/${PROJECT_ID}/tasks/*`, (route) =>
    route.fulfill({ json: mockTaskDone }),
  )
}

export async function installGenerateMocks(page: Page) {
  await installCoreMocks(page, {
    projects: [{ ...mockProject, status: 'designing' }],
  })
  await page.route(`**/api/v1/projects/${PROJECT_ID}/tasks/*`, (route) =>
    route.fulfill({ json: mockTaskRunning }),
  )
}

export { PROJECT_ID }
